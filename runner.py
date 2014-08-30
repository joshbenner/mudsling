import os
import sys
import logging

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet.error import ProcessDone

processes = {}
shutting_down = False
mudsling_root = os.path.dirname(__file__)
#src = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')


def process_ended(process, exit_code):
    if exit_code != 10:
        # 10 is the only code to indicate a restart. Otherwise, shutdown!
        global shutting_down
        shutting_down = True
        kill_all_processes()
        reactor.stop()
    else:
        process.respawn()


def kill_all_processes():
    for name, proc in processes.iteritems():
        proc.kill()


class MUDSlingProcess(protocol.ProcessProtocol):
    alive = False

    def __init__(self, name, args, gamedir):
        self.name = name
        self.args = args
        self.gamedir = gamedir

    def spawn(self):
        logging.info("Spawning %s process..." % self.name)
        scriptpath = os.path.join(mudsling_root, "%s.py" % self.name)
        args = [sys.executable, scriptpath]
        args.extend(self.args)
        reactor.spawnProcess(self,
                             executable=sys.executable,
                             args=args,
                             env=os.environ,
                             path=self.gamedir)

    def kill(self):
        if self.alive:
            logging.info("Terminating %s process..." % self.name)
            try:
                self.transport.signalProcess('TERM')
                self.alive = False  # Or it will be soon?
            except Exception as e:
                logging.warning("Cannot kill %s: %s" % (self.name, e.message))

    def respawn(self):
        processes[self.name] = MUDSlingProcess(self.name, self.args,
                                               self.gamedir)
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


def init_game_dir(path):
    """
    If game dir doesn't exist, try to create it.
    """
    path = os.path.realpath(path)
    if not path:
        logging.info("Creating game directory %s" % path)
        os.makedirs(path)
        if os.path.exists(path):
            f = open(os.path.join(path, 'settings.cfg'), 'w')
            f.close()
        else:
            raise Exception(
                "Cannot create game dir at %s" % path)
    elif not os.path.isdir(path):
        raise Exception("Game dir is a file!")
    logging.info('Using game directory: %s' % path)
    return path


def run():
    from mudsling.options import get_options

    # We are not interested in the script name part of the argv list.
    options = get_options()
    options['gamedir'] = init_game_dir(options['gamedir'])

    # Debugger means we want to keep everything in a single process.
    if '--debugger' in sys.argv:
        from server import run_server
        os.chdir(options['gamedir'])
        run_server(options)
    else:
        # Imports shouldn't resolve to this file since we added src to the
        # front of the search path above.
        from mudsling.config import config
        from mudsling.logs import open_log
        from mudsling.pid import check_pid

        argv = sys.argv[1:]

        open_log(stdout=True, level=logging.DEBUG)
        pidfile = os.path.join(options['gamedir'], 'mudsling.pid')
        check_pid(pidfile)
        config.read(options.configPaths())

        processes['server'] = MUDSlingProcess('server', argv,
                                              options['gamedir'])
        if config.getboolean('Proxy', 'enabled'):
            processes['proxy'] = MUDSlingProcess('proxy', argv,
                                                 options['gamedir'])

        for process in processes.itervalues():
            process.spawn()

        reactor.addSystemEventTrigger('before', 'shutdown', kill_all_processes)

        reactor.run()
        os.remove(pidfile)


if __name__ == '__main__':
    run()
