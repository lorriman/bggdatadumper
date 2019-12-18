import sys
import os
import hashlib

from timeit import default_timer as timer
from time import sleep
import socket
import time
import defusedxml as xmlpatcher

def init():
    
    #security: monkeypatch against attack vectors, DDos etc
    #(while unlikely, some xml hacks can get to our files)
    #also see filtering regexes in config.json
    xmlpatcher.defuse_stdlib()

def sha1_sum(filepath):
    sha1 = hashlib.sha1()
    BUF_SIZE = 65536 
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def str_to_args(args, separator=' '):
    '''prep a string to argv compatible array for Config class
    Does not include correct argv[0]. See strToArgv instead
    '''
    return [ arg.strip() for arg in args.split(separator) if arg.strip()!=''];     

def str_to_argv(args, separator=' '):
    ''''Convert string to argv ready array
    Element 0 is set to sys.argv[0] for convenience.'''
    argv0=sys.argv[0]
    argv=str_to_args(args,separator)
    argv.insert(0,argv0)
    return argv

#from https://gist.github.com/betrcode/0248f0fda894013382d7
def is_open(ip, port):
    '''support func for checking host/port is open, use checkHost instead'''

    timeout = 3
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
            s.connect((ip, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            return True
    except:
            return False
    finally:
            s.close()

def check_host(ip, port):
    '''check a service is available, ie, the python webserver for test data'''
    retry = 2
    delay = 2

    ipup = False
    for i in range(retry):
            if is_open(ip, port):
                    ipup = True
                    break
            else:
                    time.sleep(delay)
    return ipup


#utility func from https://stackoverflow.com/questions/38634988/check-if-program-runs-in-debug-mode
def is_debugging():
    '''detects if a debugger is attached'''
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        return None
    elif gettrace():
        return True
    else:
        return False

# We need a rate limiter because calls to BGG are too 
# fast for their rate limiting of 2 calls a sec
# This may be a naive implementation, but it's simple 
# and  seems to work
class RateLimiter:
    '''sleep() to limit the rate according to a minimum time between calls
    (float in seconds).
    limit() checks for elapsed time and 
    calls sleep(secs) for the difference if too fast.
    eg rl=RateLimiter(.5) will sleep on calls to .limit() if
    the time elapsed since the previous call is less than
    500 milliseconds.
    The first call to limit() starts the clock but does not 
    rate limit unless the object was initialised with a
    start_time, which avoids haivng to write awkward flow-control loops.
    '''

    def init(self,minimum,start_time=0.0):
        self.__minimum=minimum
        self.reset(start_time)

    def __init__(self,minimum=0.0, start_time=0.0):
        '''minimum is the minimum time between fetches,
    optional start_time permits starting the clock on
    initialisation eg. rl=RateLimiter(x,timer())'''

        
    #call limit to start the clock, and each time we want some limiting/sleeping
    #ie before calls to BGG since it's rate limited to 2 calls a sec
    def limit(self):
        ''' sleep if elapsed time less than minimum'''
        time_taken=timer()-self.__prev_time    
        self.__prev_time=timer()
        if time_taken < self.__minimum:            
            s=self.__minimum-time_taken
            self.__counter+=s
            sleep(s)
            #read timer again since sleep may be longer than requested
            self.__prev_time=timer()
            

    def reset(self,start_time=0.0):
        '''re-initialize but keep the minimum'''
        self.__prev_time=start_time
        self.__counter=0.0

    def count(self):
        '''Give cumulative amount of limiting, which maybe zero if
        operations are slower than the rate limit'''
        return self.__counter
