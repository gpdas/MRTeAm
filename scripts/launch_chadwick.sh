#!/bin/sh
#$ -cwd
#$ -j y
#$ -pe smp 16
#$ -l exclusive
#$ -t 1-10
#$ -V
#$ -M eric.schneider@liverpool.ac.uk
#$ -m abe

source /home/esch/.bashrc

export ROS_OS_OVERRIDE=rhel

RUN_COUNT=3
SCRIPT_DIR=~/GIT/mrta/scripts

#for map in brooklyn # smartlab
for map in smartlab
do
    for scenario_id in MR-IT-DA-scenario1 MR-CT-DA-scenario1 SR-IT-DA-scenario1 SR-CT-DA-scenario1 MR-IT-DA-scenario2 MR-CT-DA-scenario2 SR-IT-DA-scenario2 SR-CT-DA-scenario2
    do
	for mechanism in OSI SSI PSI RR
	do
	    for start_config in distributed clustered
	    do
		for run in `seq 1 ${RUN_COUNT}`
		do
		    $SCRIPT_DIR/launch_experiment.py -ng ${mechanism} ${map} ${start_config} ${scenario_id}

		done # end "run"

	    done # end "start_config"

	done # end "mechanism"

    done # end "scenario_id"

done # end "map"
