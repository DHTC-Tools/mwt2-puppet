#!/usr/bin/env python
# Importable module for lsm scripts
#
# $Id: lsm.py,v 1.1 2011/03/14 21:09:23 nathany Exp $
#
import sys, os, stat, time, syslog

# Default log file - scripts should override this
LOGFILE='/tmp/lsm.out'
sessid="%s.%s" % ( int(time.time()), os.getpid() )


def log(msg):
    try:
        f=open(LOGFILE, 'a')
        f.write("%s %s %s\n" % (time.ctime(), sessid, msg))
        f.close()
        os.chmod(LOGFILE, 0666)
    except Exception, e:
#        print e
        pass
    ident=sys.argv[0].split('/')[-1]
    try: 
        syslog.openlog(ident)
        syslog.syslog("%s %s\n" % (sessid, msg) )
    except Exception, e:
#        print e
        pass

def fail(errorcode=200,msg=None):
    if msg:
        msg='ERROR %s %s'%(errorcode, msg)
    else:
        msg='ERROR %s' % errorcode
    print msg
    log(msg)
    sys.exit(errorcode)

class Timer:
     def __init__(self):
         self.t0 = time.time()
     def __str__(self):
         return "%0.2f" % (time.time() - self.t0)
     def __float__(self):
         return time.time() - self.t0

