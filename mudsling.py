"""
Main MUDSling entry point.

Typically, this script spawns two processes: server and proxy.

However, if the --debug command line option is specified, this script will
directly execute the server and override the use of the SimpleTelnetServer.
"""
#from sys import argv
from multiprocessing import Process

#from twisted.scripts.twistd import run


def run_server():
    #argv[1:] = [
    #    '-y', 'mudsling/server.py'
    #]

    #run()
    print 'server!'


def run_proxy():
    print "I am a PROXY!"

if __name__ == '__main__':
    print 'server process'
    server = Process(target=run_server)
    #proxy = Process(target=run_proxy)
    print 'run server'
    server.start()
    #proxy.start()
    server.join()
