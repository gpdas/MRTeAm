"""
teitz_bart.py

Author Ningchuan Xiao <xiao.37@osu.edu>

https://github.com/gisalgs/optimization/blob/master/teitz_bart.py
"""


from bisect import bisect_left
from string import atoi, split
import random
import sys
#sys.path.append('../networks')
#from network2listmatrix import network2distancematrix
#from allpairdist import allpairs

INF = float('inf')

def findout(median, fi, dist, d1, d2, N):
    """
    Determines, given a candidate for insertion (fi), 
    the best candidate in the solution to replace or remove (fr).
    This does not change values in median, d1, and d2.
    """
    w = 0.0
    v = [0.0 for i in range(N)]
    for i in range(N):
        if dist[i][fi] < dist[i][d1[i]]:
            w += dist[i][d1[i]] - dist[i][fi]
        else:
            v[d1[i]] += min(dist[i][fi],
                            dist[i][d2[i]]) - dist[i][d1[i]]
    fmin = INF
    fr = 0
    for i in median:
        if v[i] < fmin:
            fmin = v[i]
            fr = i
    fmin = w-fmin
    return fmin, fr # gain and vertex to be replaced

def update_assignment(dist, median, d1, d2, p, N):
    """
    Updates d1 and d2 given median so that d1 holds the 
    nearestest facility for each node and d2 holds the second
    """
    dist1, dist2 = 0.0, 0.0
    node1, node2 = -1, -1
    for i in range(N):
        dist1, dist2 = INF, INF
        for j in range(p):
            if dist[i][median[j]] < dist1:
                dist2 = dist1
                node2 = node1
                dist1 = dist[i][median[j]]
                node1 = median[j]
            elif dist[i][median[j]] < dist2:
                dist2 = dist[i][median[j]]
                node2 = median[j]
        d1[i] = node1
        d2[i] = node2
    dist1 = 0
    for i in range(N):
        dist1 += dist[i][d1[i]]
    return dist1

def next(dist, median, d1, d2, p, N):
    """
    INPUT
      dist: distance matrix
      median: list of integers for selected vertices
      d1: list of nearest facility for each vertex
      d2: list of second nearest facility
      p: number of facilities to locate
      N: number of vertices on the nextwork
    OUPTU
      r: total distance
      median: list of integers for selected vertices
    """
    bestgain = -INF
    for i in range(N):
        gain, fr1 = findout(median, i, dist, d1, d2, N)
        if i in median:
            continue
        if gain>bestgain:
            bestgain = gain
            fr = fr1
            fi = i
    r = 0
    if bestgain > 0:
        i = median.index(fr) 
        median[i] = fi
        r = update_assignment(dist, median, d1, d2, p, N)
    return bestgain>0, r, fr, fi

def teitz_bart(dist, p, verbose=False):
    """
    INPUT
      dist: distance matrix
      p: number of facilities to be selected
      verbose: whether intermediate results are printed
    """
    N = len(dist)
    median = random.sample(range(N), p)
    d1    = [-1 for i in range(N)]
    d2    = [-1 for i in range(N)]
    r = update_assignment(dist, median, d1, d2, p , N)
    if verbose: print r
    while True:
        result = next(dist, median, d1, d2, p, N)
        if result[0]:
            r = result[1]
            if verbose: print r
        else:
            break
    return r, median

#if __name__ == "__main__":
#    print 'Problem: simple network'
#    a = network2distancematrix('../data/network-links', True)
#    allpairs(a)
#    teitz_bart(a, 2, True)
#    print 'Problem: pmed1 in OR-lib'
#    a = network2distancematrix('../data/orlib/pmed1.orlib',
#                               False)
#    allpairs(a)
#    teitz_bart(a, 5, True)
    
