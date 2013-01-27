"""
Main MUDSling entry point.

Typically, this script spawns two processes: server and proxy.

However, if the --debugger command line option is specified, this script will
directly execute the server and force the use of the SimpleTelnetServer. This
helps Python debuggers (which are notoriously poor at multiprocess debugging).
"""
from sys import argv
from multiprocessing import Process
from threading import Thread

from mudsling.twist import run_app


def process_waiter(name, target):
    p = Process(name=name, target=target)
    p.start()
    p.join()
    print "%s exited with code %d" % (p.name, p.exitcode)


def run_server():
    run_app('mudsling')


def run_proxy():
    print "I am a PROXY!"


if __name__ == '__main__':
    if '--debugger' in argv:
        run_server()
    else:
        server = Thread(target=process_waiter, args=("Server", run_server))
        proxy = Thread(target=process_waiter, args=("Proxy", run_proxy))
        server.start()
        proxy.start()
        server.join()
        proxy.join()
