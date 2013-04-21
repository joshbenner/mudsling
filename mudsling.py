import os
import sys
import logging

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet.error import ProcessDone

processes = {}
shutting_down = False
src = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')


def process_ended(process, exit_code):
    global shutting_down
    if exit_code != 10:
        # 10 is the only code to indicate a restart. Otherwise, shutdown!
        shutting_down = True
        for name, proc in processes.iteritems():
            proc.kill()
        reactor.stop()
    else:
        process.respawn()


class MUDSlingProcess(protocol.ProcessProtocol):
    alive = False

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def spawn(self):
        logging.info("Spawning %s process..." % self.name)
        args = [sys.executable, "%s.py" % self.name]
        args.extend(self.args)
        reactor.spawnProcess(self,
                             executable=sys.executable,
                             args=args,
                             env=os.environ,
                             path=src)

    def kill(self):
        if self.alive:
            logging.info("Terminating %s process..." % self.name)
            self.transport.signalProcess('KILL')

    def respawn(self):
        processes[self.name] = MUDSlingProcess(self.name, self.args)
        processes[self.name].spawn()

    def connectionMade(self):
        self.alive = True
        # todo: Can this be removed?
        self.transport.closeStdin()

    def outReceived(self, data):
        print self.name, 'out:'
        sys.stdout.write(data)

    def errReceived(self, data):
        print self.name, "err:"
        sys.stderr.write(data)

    def processExited(self, reason):
        self.alive = False
        code = 0 if isinstance(reason, ProcessDone) else reason.value.exitCode
        logging.info("%s exited with code %d" % (self.name, code))
        if not shutting_down:
            process_ended(self, code)


if __name__ == '__main__':
    # Add our src path to the beginning of the PYTHONPATH.
    sys.path.insert(0, src)

    # We are not interested in the script name part of the argv list.
    argv = sys.argv[1:]

    # Debugger means we want to keep everything in a single process.
    if '--debugger' in sys.argv:
        from server import run_server
        os.chdir(src)
        run_server(argv)
    else:
        # Imports shouldn't resolve to this file since we added src to the
        # front of the search path above.
        from mudsling.options import get_options
        from mudsling.config import config
        from mudsling.logs import open_log
        from mudsling.pid import check_pid

        options = get_options(argv)
        open_log(stdout=True, level=logging.DEBUG)
        pidfile = os.path.join(options['gamedir'], 'mudsling.pid')
        check_pid(pidfile)
        config.read(options.configPaths())

        processes['server'] = MUDSlingProcess('server', argv)
        if config.getboolean('Proxy', 'enabled'):
            processes['proxy'] = MUDSlingProcess('proxy', argv)

        for process in processes.itervalues():
            process.spawn()

        reactor.run()
        os.remove(pidfile)
