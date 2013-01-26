"""
Main MUDSling entry point.

Typically, this script spawns two processes: server and proxy.

However, if the --debugger command line option is specified, this script will
directly execute the server and override the use of the SimpleTelnetServer.
"""
from sys import argv
import argparse
from multiprocessing import Process

from twisted.scripts.twistd import run

from mudsling.twist import run_app


def run_server(args=None):
#    argv[1:] = [
#        '-y', 'mudsling/server.py'
#    ]
#    run()
    run_app('mudsling/server.py', args)

def run_proxy():
    print "I am a PROXY!"

if __name__ == '__main__':
    parser = argparse.ArgumentParser('MUDSling Game Launcher')
    parser.add_argument('--debugger', dest='debugger', action='store_const',
                        const=True, default=False)
    args = parser.parse_args()

    if args.debugger:
        run_server({'debugger': True})
    else:
        print "spawning processes..."
        server = Process(target=run_server)
        #proxy = Process(target=run_proxy)
        server.start()
        #proxy.start()
        server.join()
