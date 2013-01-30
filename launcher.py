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
import Queue

from mudsling.twist import run_app


def process_waiter(name, target, q):
    """
    Start a process and wait for it to exit. Act based on the exit code:
    - <0: Something killed the process, shutdown everything.
    -  0: Normal, purposeful exit. Shutdown everything.
    - 10: Restart process.
    -  *: Shut it all down!

    @param name: The name to give the process.
    @param target: The callable to execute for this process.
    """
    while True:
        p = Process(name=name, target=target)
        p.start()
        while p.is_alive():
            p.join(1)
            try:
                signal = q.get_nowait()
            except Queue.Empty:
                continue
            if signal == 'shutdown' and p.is_alive():
                p.terminate()
                return
        print "%s exited with code %d" % (p.name, p.exitcode)
        if p.exitcode != 10:
            try:
                q.put_nowait('shutdown')
            finally:
                return


def run_server():
    run_app('mudsling-server')


def run_proxy():
    run_app('mudsling-proxy')


if __name__ == '__main__':
    if '--debugger' in argv:
        run_server()
    else:
        q = Queue.Queue()
        server = Thread(target=process_waiter, args=("Server", run_server, q))
        proxy = Thread(target=process_waiter, args=("Proxy", run_proxy, q))
        server.start()
        proxy.start()
        server.join()
        proxy.join()
