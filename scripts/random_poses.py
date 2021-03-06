#!/usr/bin/env python

import argparse
from PIL import Image
import os.path
import random
import string
import sys

import rospkg

import pprint

import mrta.file_db

TASKS_DB_FILENAME = 'tasks.db'

DEFAULT_START_POSE_FILE = '/tmp/robot_random_starts.inc'

pp = pprint.PrettyPrinter(indent=4)


def generate_unique_id(size=8, chars=string.ascii_uppercase + string.digits):
    """ Taken from
    http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
    """
    return ''.join(random.choice(chars) for _ in range(size))


def is_valid_color(color, threshold):
    """ Return True if each component of the given color (r, g, b, a) is
        above threshold
    """
    if color[0] > threshold and color[1] > threshold and color[2] > threshold:
        return True

    return False


def is_valid_point(image, candidate_x, candidate_y, buffer):
    """ Return True if the point at (x, y) and a buffer-sized area around it
        are unoccupied

    :param image: the PIL.Image file to search
    :param candidate_x: x-coordinate of a candidate point
    :param candidate_y: y-coordinate of a candidate point
    :param buffer: nominal diameter of a robot
    """

    # We assume pure white (255, 255, 255) means unoccupied.
    # Set our threshold to 254
    threshold = 254

    for x in range((candidate_x - buffer / 2), (candidate_x + buffer / 2)):
        for y in range((candidate_y - buffer / 2), (candidate_y + buffer / 2)):

            # print "({0}, {1})".format(x, y)
            try:
                if not is_valid_color(image.getpixel((x, y)), threshold):
                    return False
            except IndexError:
                # We tried to read a pixel out of bounds (e.g. a negative coordinate)
                continue

    return True


def occupy_region(image, center_x, center_y, buffer, color):
    """ 'Occupy' a region around (x,y) with the given color """

    for x in range((center_x - buffer / 2), (center_x + buffer / 2)):
        for y in range((center_y - buffer / 2), (center_y + buffer / 2)):

            try:
                image.putpixel((x, y), color)
            except IndexError:
                # We tried to modify a pixel out of bounds (e.g. a negative coordinate)
                continue


def get_random_poses(image, num_poses, buffer_size, occupy):
    im_width, im_height = image.size

    # The random poses (pairs of (x, y, z, alpha)) to return, initially empty
    # z is always 0 and alpha is in the range [-180, 180]
    random_poses = []

    for i in range(num_poses):
        # Have we found a valid point for the robot?
        point_is_valid = False

        while not point_is_valid:

            candidate_x = random.randint(0, im_width + 1)
            # Y-coordinates start at the top of the image, not the bottom
            candidate_y = random.randint(0, im_height + 1)

            # We found a valid point
            if is_valid_point(image, candidate_x, candidate_y, buffer_size):
                alpha = round(random.uniform(-180, 180), 2)
                # Add (candidate_x, candidate_y, 0, alpha) to the list of poses to return
                # Remember that the y-axis starts from the top, so 'reverse' the value here.
                # Also, Stage needs values in meters, not cm, so divide by 100 here
                reversed_y = im_height - candidate_y
                random_poses.append((candidate_x/100.0, reversed_y/100.0, 0, alpha))

                if occupy:
                    # 'Occupy' a region around the point with a certain color,
                    # in our case RGBA black (0, 0, 0, 255)
                    occupied_color = (0, 0, 0, 255)
                    occupy_region(image, candidate_x, candidate_y, buffer_size, occupied_color)

                break
            # else:
            #     print "{2}: ({0},{1}) is not a safe location".format(candidate_x, candidate_y, i)

    return random_poses


def generate_and_write_tasks(map_image_file,
                             num_poses=8,
                             buffer_size=3,
                             scale=1.0,
                             multirobot=False,
                             constrained=False,
                             dynamic_rate=0):

    # print "map = {0}, num = {1}, size = {2}, output = {3}".format(map_image_file,
    #                                                               num_poses,
    #                                                               buffer_size,
    #                                                               output_filename)

    try:
        # Save the poses in the tasks database
        task_db = mrta.file_db.FileDB(TASKS_DB_FILENAME)
    except IOError:
        print "Couldn't write tasks to {0}! Exiting.".format(TASKS_DB_FILENAME)
        sys.exit(1)

    scenario_id = None
    scenario_in_db = True
    while scenario_in_db:
        unique_id = generate_unique_id()
        scenario_in_db = task_db.exists(scenario_id)

    scenario_id = '{0}-{1}-{2}-{3}-{4}task'.format('MR' if multirobot else 'SR',
                                                   'CT' if constrained else 'IT',
                                                   'DA' if dynamic_rate > 0 else 'SA',
                                                   unique_id,
                                                   num_poses)

    print scenario_id

    try:
        map_image = Image.open(map_image_file)
    except IOError:
        print "Couldn't open map image {0} for reading!".format(map_image_file)
        sys.exit(1)

    random_poses = get_random_poses(map_image, num_poses, buffer_size, occupy=True)

    dynamic = False
    if dynamic_rate > 0:
        dynamic = True
        # 'lambd' is the lambda parameter of a poisson distribution
        lambd = 1.0 / dynamic_rate

    task_list = []
    task_id = None
    arrival_time = 0
    for i, pose in enumerate(random_poses):
        # print "pose: [{0}, {1}, {2}, {3}]".format(*pose)

        if not task_id:
            task_id = 1

        # MR vs SR
        if multirobot:
            num_robots = random.randint(1, 2)
        else:
            num_robots = 1

        depends = []
        if constrained:
            # Flip a coin to determine if this task should be precedence-constrained to
            # a previous task. Don't try to add a constraint if this is the first task
            # in the list.
            if random.randint(0, 1) == 1 and task_list:
                random_predecessor = random.choice(task_list)
                depends.append(random_predecessor.task_id)

        new_task = mrta.SensorSweepTask(_task_id=str(task_id),
                                        x=float(pose[0]) * scale,   # x
                                        y=float(pose[1]) * scale,   # y
                                        _num_robots=num_robots,
                                        _depends=depends,
                                        _arrival_time=arrival_time)

        if dynamic:
            arrival_time += random.expovariate(lambd)

        task_list.append(new_task)
        task_id += 1

    # print("Tasks: {0}".format(pp.pformat(task_list)))
    task_db[scenario_id] = task_list
    task_db.close()


def generate_and_write_random_starts(map_image_file, num_poses=3, buffer_size=70, scale=1.0, output_filename=DEFAULT_START_POSE_FILE):

    # print "map = {0}, num = {1}, size = {2}, output = {3}".format(map_image_file,
    #                                                               num_poses,
    #                                                               buffer_size,
    #                                                               output_filename)

    try:
        map_image = Image.open(map_image_file)
    except IOError:
        print "Couldn't open map image {0} for reading!".format(map_image_file)
        sys.exit(1)

    random_poses = get_random_poses(map_image, num_poses, buffer_size, occupy=True)

    # Write the poses to output_file
    try:
        output_file = open(output_filename, 'wb')

        robot_colors = ['red', 'green', 'blue']

        for i, pose in enumerate(random_poses):
            # print "pose: [{0}, {1}, {2}, {3}]".format(*pose)
            output_file.write("turtlebot ( pose [ {0} {1} {2} {3} ] color \"{4}\" )\n".format(float(pose[0]) * scale,
                                                                                              float(pose[1]) * scale,
                                                                                              float(pose[2]) * scale,
                                                                                              pose[3],
                                                                                              robot_colors[i]))
        output_file.close()

    except IOError:
        print "Couldn't open {0} for writing! Exiting.".format(output_filename)
        sys.exit(1)


def generate_and_write_starts(map_image_file, poses, output_filename=DEFAULT_START_POSE_FILE):

    # print "map = {0}, num = {1}, size = {2}, output = {3}".format(map_image_file,
    #                                                               num_poses,
    #                                                               buffer_size,
    #                                                               output_filename)

    try:
        map_image = Image.open(map_image_file)
    except IOError:
        print "Couldn't open map image {0} for reading!".format(map_image_file)
        sys.exit(1)

    # Write the poses to output_file
    try:
        output_file = open(output_filename, 'wb')

        robot_colors = ['red', 'green', 'blue']

        for i, pose in enumerate(poses):
            # print "pose: [{0}, {1}, {2}, {3}]".format(*pose)
            output_file.write("turtlebot ( pose [ {0} {1} {2} {3} ] color \"{4}\" )\n".format(pose[0],
                                                                                              pose[1],
                                                                                              # pose[2],
                                                                                              0,
                                                                                              # pose[3],
                                                                                              0,
                                                                                              robot_colors[i]))

        output_file.close()

    except IOError:
        print "Couldn't open {0} for writing! Exiting.".format(output_filename)
        sys.exit(1)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate a stage world file containing random starting poses.')

    parser.add_argument('pose_type',
                        choices=['starts', 'tasks', 'manual-starts'],
                        help='The type of random poses to generate.')

    # Fix this
    parser.add_argument('map_image_file',
                        help='The map file (e.g., .png) to use.')

    parser.add_argument('-n', '--num_poses',
                        help='The number of robots/poses to generate',
                        default=3)

    parser.add_argument('-b', '--buffer_size',
                        help='(Square) footprint around a pose to avoid picking subsequent poses (in cm/pixels)',
                        default=70)

    parser.add_argument('-s', '--scale',
                        help='Pixel to cm scaling factor',
                        default=1.0)

    parser.add_argument('-o', '--output_file',
                        help='Name of the Stage .inc file to write robot poses.',
                        default="/tmp/robot_random_starts.inc")

    parser.add_argument('-p', '--poses',
                        help='A space-separated list of (x,y) pairs of robot start positions.',
                        nargs='+', type=float,
                        default=[])

    parser.add_argument('-m', '--multirobot',
                        help='For each task, randomly decide the number of robots required (currently either 1 or 2).',
                        action="store_true")

    parser.add_argument('-c', '--constrained',
                        help='For each task, randomly choose a previously-defined task for this task to depend on.',
                        action="store_true")

    parser.add_argument('-d', '--dynamic_rate',
                        help='Rate at which dynamic tasks should appear, in seconds. E.g., \'30\' means a task ' +
                        'should appear, on average, every 30 seconds. A value of 0 means all tasks are static.',
                        type=float,
                        default=0)

    args = parser.parse_args()

    map_image_file = args.map_image_file
    num_poses = int(args.num_poses)
    buffer_size = int(args.buffer_size)
    scale = float(args.scale)
    output_file = args.output_file
    poses = args.poses
    multirobot = args.multirobot
    constrained = args.constrained
    dynamic_rate = args.dynamic_rate

    # print("num_poses: {0}".format(num_poses))
    # print("poses: {0}".format(poses))

    if args.pose_type == 'starts':
        generate_and_write_random_starts(map_image_file, num_poses, buffer_size, scale, output_file)
    elif args.pose_type == 'tasks':
        generate_and_write_tasks(map_image_file, num_poses, buffer_size, scale, multirobot, constrained, dynamic_rate)
    elif args.pose_type == 'manual-starts':
        pose_list = []
        for i in range(num_poses):
            pose_list.append((poses[i*2], poses[i*2+1]))
        generate_and_write_starts(map_image_file, pose_list, output_file)

