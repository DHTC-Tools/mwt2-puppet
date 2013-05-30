#!/usr/bin/env python

_id = "3.0.2p6"

import sys, os, errno, fcntl, stat, time, getopt, re, select, signal
from urllib import urlopen, urlencode
from socket import gethostname

# Log message levels
DEBUG, INFO, WARN, ERROR = "DEBUG", "INFO", "WARN", "ERROR"

# filename for locking 
LOCK_NAME = ".LOCK"

def _sigchld(*args):
    pass

def unitize(x):
    suff='BKMGTPEZY'
    while x >= 1024 and suff:
        x /= 1024.0
        suff = suff[1:]
    return "%.4g%s" % (x, suff[0])

class Pcache:
    def Usage(self):
        print>>sys.stderr, """Usage:
        %s [flags] copy_prog [copy_flags] input output""" % self.progname
##      print>>sys.stderr, "  flags are: "
#  "s:r:m:A:R:t:r:g:fFl:VvqpH:S:",
#  "scratch-dir=",
#  "storage-root=",
#  "max-space=",
#  "hysterisis=",
#  "accept=",
#  "reject=",
#  "timeout=",
#  "retry=",
#  "force",
#  "flush-cache",
#  "guid=",
#  "log=",
#  "version",
#  "verbose",
#  "debug",
#  "quiet",
#  "panda",
#  "hostname",
#  "sitename"

    def __init__(self): #set defaults values
        os.umask(0)
            
        self.storage_root = "/pnfs"
        self.scratch_dir = "/scratch/"
        self.pcache_dir = self.scratch_dir + "pcache/"
        self.log_file = self.pcache_dir + "pcache.log"
        self.max_space = "80%"
        self.hysterisis = 0.9
        self.transfer_timeout = "600"
        self.max_retries = 3
        self.guid = None
        self.accept_patterns = []
        self.reject_patterns = []
        self.force = False
        self.flush = False
        self.verbose = False
        self.quiet = False
        self.debug = False
        self.hostname = None
        self.sitename = None # XXX can we get this from somewhere?
        self.update_panda = False
        self.panda_url = "https://pandaserver.cern.ch:25443/server/panda/"
        ## Development - "https://voatlas48.cern.ch:25443/server/panda/"
        ## Production - "https://pandaserver.cern.ch:25443/server/panda/" 

        ## internal variables
        self.sleep_interval = 15
        self.force = False
        self.locks = {}
        self.deleted_guids = []
        self.version = _id

        
    def parse_args(self, args):
        ## handle pcache flags and leave the rest in self.args
        try:
            opts, args = getopt.getopt(args,
                                       "s:x:m:y:A:R:t:r:g:fFl:VvdqpPH:S:",
                                       ["scratch-dir=",
                                        "storage-root=",
                                        "max-space=",
                                        "hysterisis=",
                                        "accept=",
                                        "reject=",
                                        "timeout=",
                                        "retry=",
                                        "force",
                                        "flush-cache",
                                        "guid=",
                                        "log=",
                                        "version",
                                        "verbose",
                                        "debug",
                                        "quiet",
                                        "print-stats",
                                        "panda",
                                        "hostname",
                                        "sitename"])
            
            ### XXXX cache, stats, reset, clean, delete, inventory
            ### TODO: move checksum/size validation from lsm to pcache
        except getopt.GetoptError, err:
            sys.stderr.write("%s\n"% err)
            self.Usage()
            self.fail(2)

        for opt, arg in opts:
            if opt in ("-s", "--scratch-dir"):
                self.scratch_dir = arg
                # Make sure scratch_dir endswith /
                if not self.scratch_dir.endswith("/"):
                    self.scratch_dir += "/"
                self.pcache_dir = self.scratch_dir + "pcache/"
                self.log_file = self.pcache_dir + "pcache.log"
            elif opt in ("-x", "--storage-root"):
                self.storage_root = arg
            elif opt in ("-m", "--max-space"):
                self.max_space = arg
            elif opt in ("-y", "--hysterisis"):
                if arg.endswith('%'):
                    self.hysterisis = float(arg[:-1]) / 100
                else:
                    self.hysterisis = float(arg)
            elif opt in ("-A", "--accept"):
                self.accept_patterns.append(arg)
            elif opt in ("-R", "--reject"):
                self.reject_patterns.append(arg)
            elif opt in ("-t", "--timeout"):
                self.transfer_timeout = arg
            elif opt in ("-f", "--force"):
                self.force = True
            elif opt in ("-F", "--flush-cache"):
                self.flush = True
            elif opt in ("-g", "--guid"):
                self.guid = arg
            elif opt in ("-r", "--retry"):
                self.max_retries = int(arg)
            elif opt in ("-V", "--version"):
                print self.version
                sys.exit(0)
            elif opt in ("-l", "--log"):
                self.log_file = arg
            elif opt in ("-v", "--verbose"):
                self.verbose = True
            elif opt in ("-d", "--debug"):
                self.debug = True
            elif opt in ("-q", "--quiet"):
                self.quiet = True
            elif opt in ("-p", "--print-stats"):
                self.print_stats()
                sys.exit(0)
            elif opt in ("-P", "--panda"):
                self.update_panda = True
            elif opt in ("-H", "--hostname"):
                self.hostname = arg
            elif opt in ("-S", "--sitename"):
                self.sitename = arg

        # Convert max_space arg to percent_max or bytes_max
        if self.max_space.endswith('%'): 
            self.percent_max = float(self.max_space[:-1])
            self.bytes_max = None
        else: # handle suffix
            self.percent_max = None
            m = self.max_space.upper()
            index = "BKMGTPEZY".find(m[-1])
            if index >= 0:
                self.bytes_max = float(m[:-1]) * (1024**index)
            else:  #Numeric value w/o units (exception if invalid)
                self.bytes_max = float(self.max_space)

        # Convert timeout to seconds    
        t = self.transfer_timeout
        mult = 1
        suff = t[-1]
        if suff in ('H', 'h'):
            mult = 3600
            t = t[:-1]
        elif suff in ('M', 'm'):
            mult = 60
            t = t[:1]
        elif suff in ('S', 's'):
            mult = 1
            t = t[:-1]
        self.transfer_timeout = mult * int(t)

        # Pre-compile regexes
        self.accept_patterns = map(re.compile, self.accept_patterns)
        reject_patterns = map(re.compile, self.reject_patterns)

        # Set host and name
        if self.hostname is None:
            self.hostname = gethostname()
        if self.sitename is None:
            self.sitename = os.environ.get("SITE", "") #XXXX
        
        # All done
        self.args = args


    def main(self, args):
        self.cmdline = ' '.join(args)
        self.t0 = time.time()
        self.progname = args[0] or "pcache"
        if self.parse_args(args[1:]):
            self.Usage()
            return 1

        if not os.path.exists(self.pcache_dir) and self.update_panda:
            self.panda_flush_cache() # cache dir may have been wiped
        if self.mkdir_p(self.pcache_dir):
            return 3
        self.log(INFO, "%s version %s invoked as: %s",
                 self.progname, self.version, self.cmdline)

        if self.flush:
            if self.args:
                print>>sys.stderr, "--flush not compatible with other options"
                self.fail(2)
            else:
                self.flush_cache()
                sys.exit(0)

        if len(self.args) < 3:  ## XXX Fail on extra args
            self.Usage()
            self.fail(2)

        self.copy_util = self.args[0]
        self.copy_args = self.args[1:-2]
        self.src = self.args[-2]
        self.dst = self.args[-1]
        self.dst_prefix = ''

        if self.dst.startswith('file:'):
            self.dst_prefix = 'file:'
            self.dst = self.dst[5:]
            # Leave one '/' on dst
            while len(self.dst) > 1 and self.dst[1] == '/':
                self.dst_prefix += '/'
                self.dst = self.dst[1:]
            
        if not (self.dst.startswith(self.scratch_dir) and
                self.accept(self.src) and not self.reject(self.src)):
            ## Execute original command, no further action
            status = os.execvp(self.copy_util, self.args)
            os._exit(1) 

        ### XXXX todo:  fast-path - try to acquire lock
        # first, if that succeeds, don't call
        # create_pcache_dst_dir

        # load file into pcache 
        self.create_pcache_dst_dir()
        ### XXXX TODO _ dst_dir can get deleted before lock!
        waited = False
        
        # If another transfer is active, lock_dir will block
        if self.lock_dir(self.pcache_dst_dir, blocking=False):
            waited = True
            self.log(INFO, "%s locked, waiting", self.pcache_dst_dir)
            self.lock_dir(self.pcache_dst_dir, blocking=True)

        if waited:
            self.log(INFO, "waited %.2f secs", time.time() - self.t0)

        if self.force:
            self.empty_dir(self.pcache_dst_dir)

        status = None
        cache_file = self.pcache_dst_dir + "data"
        if os.path.exists(cache_file):
            self.log(INFO, "cache hit %s", self.src)
            self.update_stats("cache_hits")
            self.finish()
        else:
            self.update_stats("cache_misses")
            status = self.pcache_copy_in()
            if not status:
                self.finish()
        self.unlock_dir(self.pcache_dst_dir)
        self.log(INFO, "total time %.2f secs", time.time() - self.t0)
        self.maybe_start_cleaner_thread()
        return status

    def finish(self):
        self.update_mru()
        cache_file = self.pcache_dst_dir + "data"
        if self.make_hard_link(cache_file, self.dst):
            self.fail()

    def pcache_copy_in(self):
        cache_file = self.pcache_dst_dir + "data"
        #record source URL
        try:
            fname = self.pcache_dst_dir+"src"
            f = open(fname, 'w')
            f.write(self.src + '\n')
            f.close()
            self.chmod(fname, 0666)
        except:
            pass
        #record GUID if given
        if self.guid:
            try:
                fname = self.pcache_dst_dir+"guid"
                f = open(fname, 'w')
                f.write(self.guid + '\n')
                f.close()
                self.chmod(fname, 0666)
            except:
                pass

        retry = 0
        while retry <= self.max_retries:
            if retry:
                self.log(INFO, "do_transfer: retry %s", retry)
            status = self.do_transfer()
            if not status: # Success, no error
                break
            retry += 1

        if (not status):
            self.update_cache_size(os.stat(cache_file).st_size)
            if self.guid and self.update_panda:
                self.panda_add_cache_files((self.guid,))
                
        return status
    
    def create_pcache_dst_dir(self):
        d = self.src
        index = d.find(self.storage_root)
        if index >= 0:
            d = d[index:]
        else:
            index = d.find("SFN=")
            if index >= 0:
                d = d[index+4:]
        ### XXXX any more patterns to look for?
        d = os.path.normpath(self.pcache_dir+"CACHE/"+d)
        if not d.endswith('/'):
            d += '/'
        self.pcache_dst_dir = d
        status = self.mkdir_p(d)
        if status:
            self.log(ERROR, "mkdir %s %s", d, status)
            self.fail()

    def get_disk_usage(self):
        p = os.popen("df -P %s | tail -1" % self.pcache_dir, 'r')
        data = p.read()
        status = p.close()
        if status:
            self.log(ERROR, "get_disk_usage: df command failed, status=%s", status)
            sys.exit(1)
        tok = data.split()
        percent = tok[-2]
        if not percent.endswith('%'):
            self.log(ERROR, "get_disk_usage: cannot parse df output: %s", data)
            sys.exit(1)
        percent = int(percent[:-1])
        return percent

    def over_limit(self, factor=1.0):
        if self.percent_max:
            return self.get_disk_usage() > factor*self.percent_max
        if self.bytes_max:
            return self.get_cache_size() > factor*self.bytes_max
        return False

    
    def clean_cache(self):
        t0 = time.time()
        self.log(INFO, "starting cleanup, cache size=%s, usage=%s%%",
                 self.get_cache_size(),
                 self.get_disk_usage())
        for l in self.list_by_mru():
            try:
                d = os.readlink(l)
            except OSError, e:
                self.log(ERROR, "readlink: %s", e)
                continue
            self.log(DEBUG, "deleting %s", d)
            self.empty_dir(d)
            
            ## empty_dir should also delete MRU symlink, but
            ## mop up here in there is some problem with the
            ## backlink
            try:
                os.unlink(l)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    self.log(ERROR, "unlink: %s", e)
            if not self.over_limit(self.hysterisis):
                break
        self.log(INFO, "cleanup complete, cache size=%s, usage=%s%%, time=%.2f secs",
                 self.get_cache_size(),
                 self.get_disk_usage(),
                 time.time() - t0)


    def list_by_mru(self):
        mru_dir = self.pcache_dir + "MRU/"
        for root, dirs, files in os.walk(mru_dir):
            dirs.sort()
            for d in dirs:
                path = os.path.join(root,d)
                if os.path.islink(path):
                    dirs.remove(d)
                    yield path
            if files:
                files.sort()
                for file in files:
                    path = os.path.join(root, file)
                    yield path

    def flush_cache(self):
        # Delete everything in CACHE, MRU, and reset stats
        self.log(INFO, "flushing cache")
        if self.update_panda:
            self.panda_flush_cache()
        self.reset_stats()
        ts = '.'+str(time.time())
        for d in "CACHE", "MRU":
            d = self.pcache_dir + d
            try:
                os.rename(d, d+ts)
                os.system("rm -rf %s &" % (d+ts))
            except OSError, e:
                if e.errno != errno.ENOENT:
                    self.log(ERROR, "%s: %s", d, e)

    def do_transfer(self):
        cache_file = self.pcache_dst_dir + "data"
        xfer_file = self.pcache_dst_dir + "xfer"
        try:
            os.unlink(xfer_file)
        except OSError, e:
            if e.errno != errno.ENOENT:
                self.log(ERROR, "unlink: %s", e)
        
        #modify command line to point to pcache area
        args = self.args[:]
        copy_util = args[0]
        args[-1] = self.dst_prefix + xfer_file

        signal.signal(signal.SIGCHLD, _sigchld) #needed to break 'select'
        pid = os.fork()

        if pid == 0: # Child
            try:
                os.execvp(copy_util, args)
                os._exit(1) # should not get here
            except OSError, e:
                self.log(ERROR, "execvp(%s): %s", copy_util, e)
                os._exit(1)
            return 1

        # Parent
        t0 = time.time()
        child_pid = pid
        exit_status = None
        self.log(INFO, "starting pid=%s, %s", child_pid, ' '.join(args))
        end = t0 + self.transfer_timeout
        now = time.time()
        while now < end:
            now = time.time()
            self.log(DEBUG, "t=%s, waitpid(%s, WNOHANG)", now, child_pid)
            done_pid, status = os.waitpid(child_pid, os.WNOHANG)
            self.log(DEBUG, "waitpid returns %s, %s", done_pid, status)
            if done_pid == child_pid:
                exit_status = os.WEXITSTATUS(status)
                self.log(INFO, "pid %s exited, status=%s", child_pid, exit_status)
                break
            remaining = max(end - time.time(), 0)
            timeout = min(remaining, self.sleep_interval)
            self.log(DEBUG, "going to select for %s" , timeout)
            try:
                select.select([], [], [], timeout)
            except select.error, e:
                if e[0] != errno.EINTR:
                    self.log(WARN, "select: %s", e[1])

            self.log(DEBUG, "select exits, t=%s", time.time())
        else: # Failed
            try:
                os.kill(child_pid, signal.SIGTERM)
                time.sleep(1)
                os.kill(child_pid, signal.SIGKILL)
                os.waitpid(child_pid, os.WNOHANG)
            except OSError, e:
                self.log(WARN, "kill: %s", e)
            return 1

        if exit_status or not os.path.exists(xfer_file):
            self.log(INFO, "copy command failed, elapsed time = %.2f sec", time.time() - t0)
            self.cleanup_failed_transfer()
            return 1
        self.log(INFO, "copy command succeeded, elapsed time = %.2f sec", time.time() - t0)
        try:
            os.rename(xfer_file, cache_file)
            ##self.log(INFO, "rename %s %s", xfer_file, cache_file)
        except OSError, e: # Fatal error if we can't do this
            self.log(ERROR, "rename %s %s", xfer_file, cache_file)
            try:
                os.unlink(xfer_file)
            except:
                pass
            self.fail()
        ##XXXX should we do this chmod?
        self.chmod(cache_file, 0666)
        return  #Success
    
    def maybe_start_cleaner_thread(self):
        if not self.over_limit():
            return
        # exit immediately if another cleaner is active
        cleaner_lock = os.path.join(self.pcache_dir, ".clean")
        if self.lock_file(cleaner_lock, blocking=False):
            self.log(INFO, "cleanup not starting:  %s locked", cleaner_lock)
            return
        # see http://www.faqs.org/faqs/unix-faq/faq/part3/section-13.html
        # for explanation of double-fork
        pid = os.fork()
        if pid: # parent
            os.waitpid(pid, 0)
            return
        else: # child
            self.daemonize()
            pid = os.fork()
            if pid:
                os._exit(0)
            ##grandchild
            self.clean_cache()
            self.unlock_file(cleaner_lock)
            os._exit(0)
            
    def make_hard_link(self, src, dst):
        self.log(INFO, "linking %s to %s", src, dst)
        try:
            if os.path.exists(dst):
                os.unlink(dst)
            os.link(src,dst)
        except OSError, e:
            self.log(ERROR, "make_hard_link: %s", e)
            ret = e.errno
            if ret == errno.ENOENT:
                try:
                    stat_info = os.stat(src)
                    self.log(INFO, "stat(%s) = %s", src, stat_info)
                except:
                    self.log(INFO, "cannot stat %s", src)
                try:
                    stat_info = os.stat(dst)
                    self.log(INFO, "stat(%s) = %s", dst, stat_info)
                except:
                    self.log(INFO, "cannot stat %s", dst)                    
            return ret
    
    def reject(self, name):
        for pat in self.reject_patterns:
            if pat.search(name):
                return True
        return False

    def accept(self, name):
        if not self.accept_patterns:
            return True
        for pat in self.accept_patterns:
            if pat.search(name):
                return True
        return False

    def get_stat(self, stats_dir, stat_name):
        filename = os.path.join(self.pcache_dir, stats_dir, stat_name)
        try:
            f = open(filename, 'r') 
            data = int(f.read().strip())
            f.close()
        except:
            data = 0
        return data
    
    def print_stats(self):
        print "Cache size:", unitize(self.get_stat("CACHE", "size"))
        print "Cache hits:", self.get_stat("stats", "cache_hits")
        print "Cache misses:", self.get_stat("stats", "cache_misses")

    def reset_stats(self):
        stats_dir = os.path.join(self.pcache_dir, "stats")
        try:
            for f in os.listdir(stats_dir):
                try:
                    os.unlink(os.path.join(stats_dir,f))
                except:
                    pass
        except:
            pass
        #XXXX error handling
        pass

    def update_stat_file(self, stats_dir, name, delta): #internal
        stats_dir = os.path.join(self.pcache_dir, stats_dir)
        self.mkdir_p(stats_dir)
        self.lock_dir(stats_dir)
        stats_file = os.path.join(stats_dir, name)
        try:
            f = open(stats_file, 'r')
            data = f.read()
            f.close()
            value = int(data)
        except:
            #### XXXX
            value = 0
        value += delta
        try:
            f = open(stats_file, 'w')
            f.write("%s\n" % value)
            f.close()
            self.chmod(stats_file, 0666)
        except:
            pass
            #### XXX
        self.unlock_dir(stats_dir)

    def update_stats(self, name, delta=1):
        return self.update_stat_file("stats", name, delta)

    def update_cache_size(self, bytes):
        return self.update_stat_file("CACHE", "size", bytes)

    def get_cache_size(self):
        filename =os.path.join(self.pcache_dir, "CACHE", "size")
        size = 0
        try:
            f = open(filename)
            data = f.read()
            size = int(data)
        except:
            pass
        if size == 0:
            size = self.do_cache_inventory()
        return size

    def do_cache_inventory(self):
        inventory_lock = os.path.join(self.pcache_dir, ".inventory")
        if self.lock_file(inventory_lock, blocking=False):
            return
        size = 0
        self.log(INFO, "starting inventory")
        for root, dirs, files in os.walk(self.pcache_dir):
            for f in files:
                if f == "data":
                    fullname = os.path.join(root, f)
                    try:
                        size += os.stat(fullname).st_size
                    except OSError, e:
                        self.log(ERROR, "stat(%s): %s", fullname, e)
        filename = os.path.join(self.pcache_dir, "CACHE", "size")
        try:
            f = open(filename, 'w')
            f.write("%s\n" % size)
            f.close()
            self.chmod(filename, 0666)
        except:
            pass  #XXXX
        self.unlock_file(inventory_lock)
        self.log(INFO, "inventory complete, cache size %s", size)
        return size

    def daemonize(self):
        if self.debug:
            return
        try:
            os.setsid()
        except OSError:
            pass
        try:
            os.chdir("/")
        except OSError:
            pass
        try:
            os.umask(0)
        except OSError:
            pass
        n = os.open("/dev/null", os.O_RDWR)
        i, o, e =  sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()
        os.dup2(n, i)
        os.dup2(n, o)
        os.dup2(n, e)
        MAXFD = 1024
        try:
            import resource# Resource usage information.
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if (maxfd == resource.RLIM_INFINITY):
                maxfd = MAXFD
        except:
            try:
                maxfd = os.sysconf("SC_OPEN_MAX")
            except:
                maxfd = MAXFD # use default value
        for fd in xrange(0, maxfd+1):
            try:
                os.close(fd)
            except:
                pass


    ## Panda server callback functions
    def do_http_post(self, url, data):
        # see http://www.faqs.org/faqs/unix-faq/faq/part3/section-13.html
        # for explanation of double-fork (is it overkill here?)
        pid = os.fork()
        if pid: # parent
            os.waitpid(pid, 0)
            return
        else: # child
            self.daemonize()
            pid = os.fork()
            if pid:
                os._exit(0)
            ##grandchild
            retry = 0
            ## This will retry for up to 1 hour, at 2 minute intervals
            while retry < 30:
                try:
                    u = urlopen(url, data=urlencode(data))
                    ret = u.read()
                    u.close()
                    self.log(INFO, "http post to %s, retry %s, data='%s', return='%s'",
                             url, retry, data, ret)
                    if ret == "True":
                        break
                except:
                    exc, msg, tb = sys.exc_info()
                    self.log(ERROR, "post to %s, data=%s, error=%s", url, data, msg)
                retry += 1
                time.sleep(120)
            #finished, don't keep the child thread around!
            os._exit(0)
                    
    def panda_flush_cache(self):
        self.do_http_post(self.panda_url + "flushCacheDB",
                          data={"site":self.sitename,
                                "node":self.hostname})

    def panda_add_cache_files(self, guids):
        self.do_http_post(self.panda_url + "addFilesToCacheDB",
                          data={"site":self.sitename,
                                "node":self.hostname,
                                "guids":','.join(guids)})

    def panda_del_cache_files(self, guids):
        self.do_http_post(self.panda_url + "deleteFilesFromCacheDB",
                          data={"site":self.sitename,
                                "node":self.hostname,
                                "guids":','.join(guids)})
        
    ## Locking functions
    def lock_dir(self, d, create=True, blocking=True):
        lock_name = os.path.join(d, LOCK_NAME)
        status = self.lock_file(lock_name, blocking)
        if not status: # succeeded
            return
        if status == errno.ENOENT and create:
            status = self.mkdir_p(d)
            if status:
                self.log(ERROR, "mkdir %s %s", d, status)
                self.fail()
            status = self.lock_file(lock_name, blocking)
        return status

    def unlock_dir(self, d):
        return self.unlock_file(os.path.join(d, LOCK_NAME))
        
    def lock_file(self, name, blocking=True):
        if self.locks.has_key(name):
            self.log(DEBUG, "lock_file: %s already locked", name)
            return
        try:
            f = open(name, 'w')
        except IOError, e:
            self.log(ERROR, "open: %s", e)
            return e.errno
            
        self.locks[name] = f
        flag = fcntl.LOCK_EX
        if not blocking:
            flag |= fcntl.LOCK_NB
        while True:
            try:
                status = fcntl.lockf(f, flag)
                break
            except IOError, e:
                if e.errno in (errno.EAGAIN, errno.EACCES) and not blocking:
                    f.close()
                    del self.locks[name]
                    return e.errno
                if e.errno != errno.EINTR:
                    status = e.errno
                    log(ERROR, "lockf: %s", e)
                    self.fail()
        return status
        
    def unlock_file(self, name):
        f = self.locks.get(name)
        if not f:
            self.log(DEBUG, "unlock_file: %s not locked", name)
            return

        ## XXXX does this create a possible race condition?
        if 0:
            try:
                os.unlink(name)
            except:
                pass
        status = fcntl.lockf(f, fcntl.LOCK_UN)
        f.close()
        del self.locks[name]
        return status
    
    def unlock_all(self):
        for filename, f in self.locks.items():
            try:
                f.close()
                os.unlink(filename)
            except:
                pass
            
    # Cleanup functions
    def delete_file_and_parents(self, name):
        try:
            os.unlink(name)
        except OSError, e:
            if e.errno != errno.ENOENT:
                self.log(ERROR, "unlink: %s", e)
                self.fail()
        self.delete_parents_recursive(name)

    def delete_parents_recursive(self, name): #internal
        try:
            dirname = os.path.dirname(name)
            if not os.listdir(dirname):
                os.rmdir(dirname)
                self.delete_parents_recursive(dirname)
        except OSError, e:
            self.log(DEBUG, "delete_parents_recursive: %s", e)

    def update_mru(self):
        now = time.time()
        link_to_mru = self.pcache_dst_dir + "mru"
        if os.path.exists(link_to_mru):
            l = os.readlink(link_to_mru)
            self.delete_file_and_parents(l)



        try:
            os.unlink(link_to_mru)
        except OSError, e:
            if e.errno != errno.ENOENT:
                self.log(ERROR, "unlink: %s", e)
                self.fail()

        mru_dir = self.pcache_dir + "MRU/" + time.strftime("%Y/%m/%d/%H/%M/",
                                                           time.localtime(now))

        self.mkdir_p(mru_dir)

# Create the link from MRU dir to CACHE dir, eg
# /scratch/pcache/MRU/2011/04/27/15/40/54.557 -->
#   /scratch/pcache/CACHE/pnfs/uchicago.edu/atlasuserdisk/user.lweithof/user.lweithof.0427201147.995031.lib._003033/user.lweithof.0427201147.995031.lib._003033.lib.tgz/

        #if os.path.exists(link_from_mru):
        ## XXX is racy!

        name = "%.3f" % (now%60)
        ext = 0
        while True:
            if ext:
                link_from_mru = "%s%s-%s" % (mru_dir, name, ext)
            else:
                link_from_mru = "%s%s" % (mru_dir, name)

            try:
                os.symlink(self.pcache_dst_dir, link_from_mru)
                break
            except OSError, e:
                if e.errno == errno.EEXIST:
                    ext += 1 # add an extension & retry if file exists
                    continue
                else:
                    self.log(ERROR, "symlink: %s %s", e, link_from_mru)
                    self.fail()
                    
        while True:
            try:
                os.symlink(link_from_mru, link_to_mru)
                break
            except OSError, e:
                if e.errno == errno.EEXIST:
                    try:
                        os.unlink(link_to_mru)
                    except OSError, e:
                        if e.errno != errno.ENOENT:
                            self.log(ERROR, "unlink: %s %s", e, link_to_mru)
                            self.fail()
                else:
                    self.log(ERROR, "symlink: %s %s", e, link_from_mru)
                    self.fail()
            
    def cleanup_failed_transfer(self):
        try:
            os.unlink(self.pcache_dir+'xfer')
        except:
            pass 
            
    def empty_dir(self, d):
        status = None
        bytes_deleted = 0
        for name in os.listdir(d):
            size = 0
            fullname = os.path.join(d,name)
            if name == "data":
                try:
                    size = os.stat(fullname).st_size
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        self.log(WARN, "stat: %s", e)
            elif name == "guid":
                try:
                    guid=open(fullname).read().strip()
                    self.deleted_guids.append(guids)
                except:
                    pass # XXXX
            elif name == "mru" and os.path.islink(fullname):
                try:
                    mru_file = os.readlink(fullname)
                    os.unlink(fullname)
                    self.delete_file_and_parents(mru_file)
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        self.log(WARN, "empty_dir: %s", e)
            try:
                if self.debug:
                    print "UNLINK", fullname
                os.unlink(fullname)
                bytes_deleted += size
            except OSError, e:
                if e.errno != errno.ENOENT:
                    self.log(WARN, "empty_dir2: %s", e)
                ##self.fail()
        self.update_cache_size(-bytes_deleted)
        self.delete_parents_recursive(d)
        return status

    def chmod(self, path, mode):
        try:
            os.chmod(path, mode)
        except OSError, e:
            if e.errno != errno.EPERM: #Cannot chmod files we don't own!
                self.log(ERROR, "chmod %s %s", path, e)
            
    def mkdir_p(self, d, mode=0777):
        ## Thread-safe
        try:
            os.makedirs(d, mode)
            return 0
        except OSError, e:
            if e.errno == errno.EEXIST:
                pass
            else:
                # Don't use log here, log dir may not exist
                print >> sys.stderr, e
                return e.errno
        
    def log(self, level, msg, *args):
        if self.quiet:
            return # Disable all logging
        if level == DEBUG and not self.debug:
            return

        msg = "%s %s %s %s %s\n" % (
            time.strftime("%F %H:%M:%S"),
            self.hostname,
            os.getpid(),
            level,
            str(msg)%args)
        try:
            f = open(self.log_file, "a+", 0666)
            f.write(msg)
            f.close()
        except Exception, e:
            sys.stderr.write("%s\n" % e)
            sys.stderr.write(msg)
            sys.stderr.flush()
        if self.debug or self.verbose or level==ERROR:
            sys.stderr.write(msg)
            sys.stderr.flush()
            
    def fail(self, errcode=1):
        self.unlock_all()
        sys.exit(errcode)

if __name__ == "__main__":
    p=Pcache()
    args = sys.argv
    if args == ['']:
        ## for testing
        args = ["pcache", "-v", "cp", "/tmp/x", "/scratch/test/x"]
    status=p.main(args)
    sys.exit(status)
