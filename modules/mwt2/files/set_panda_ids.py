#!/usr/bin/python

MC_HOSTLIST=['mc.mwt2.org:11211']
CLUSTER_ID="MWT2"
server_name="osg-gk.mwt2.org"

import os,sys,time, re, string
from cStringIO import StringIO
from socket import gethostname
import memcache
mc = None
TTL = 30 * 60 ## 30 minutes
verbose=0

def mc_init():
    global mc
    if not mc:
        mc = memcache.Client(MC_HOSTLIST)

def mc_set_multi(d, ttl=TTL):
    mc_init()
    try:
        mc.set_multi(d, ttl)
    except Exception, e:
        print e
        pass
    if verbose > 1:
        print "SET multi", d

def mc_get_multi1(k):
    mc_init()
    d={}.fromkeys(k, None)
    d1={}
    try:
       d1 = mc.get_multi(k)
    except Exception, e:
       if verbose > 1:
          print e
       pass
    if verbose > 1:
       print "GET multi", d1
    d.update(d1)
    return d

def mc_get_multi(k):
    mc_init()
    try:
        d = mc.get_multi(k)
    except exception, e:
        if verbose > 1:
           print e
        pass
    if verbose > 1:
        print "GET multi", d
    return d




def get_pstree():
    pstree={}
    #p = os.popen("pstree -pal $( ps -A --forest | grep -m1 condor_startd | awk '{ print $1}' )  2>&1 | tac")
    p = os.popen("pstree -pal $( cat /var/run/condor/condor.pid )  2>&1 | tac")
    lines = p.readlines()
    status = p.close()
    for line in lines:
        if 'Usage:' in line:
            print "Error running pstree on", host
    if status:
        if verbose:
            print host, "pstree failed", status
        return pstree
    tmp = []
    sess = 'Master'
    for line in lines[1:]:
#        print line[8:22]
        if line[8:22] == 'condor_starter': # new session entry
            sess=line.split(',')[1].split(' ')[3]
            if tmp:
                pstree[sess] = tmp
                tmp = []
        tmp.append(line)
    # last one
    pstree[sess] = tmp
    return pstree
host = gethostname().split('.')[0]
pstree = get_pstree()
pat = re.compile("PandaJob_([0-9]+)_")
multi={}
condor_job_ids=mc_get_multi( [ "%s.%s" % (host, slot[4:]) 
	for slot in pstree.keys()] )
#print pstree
for slot in pstree.keys():
   #print "Observing %s" % slot
   #print pstree[slot]
   try:
     lines = pstree[slot]
     for line in lines:
       match = pat.search(line)
       if match:
         panda_id = match.group(1)
         #print panda_id
         multi["%s.panda_id" % condor_job_ids["%s.%s" % (host, slot[4:])]] = panda_id
         break
   except KeyError:
     if verbose:
       exc, msg, tb = sys.exc_info()
       print exc, msg
mc_set_multi(multi)
