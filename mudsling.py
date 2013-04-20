import os
import sys

from twisted.internet import reactor
from twisted.internet import protocol

processes = {}


def process_ended(name, reason):
    print "%s ended: %r" % (name, reason)
    reactor.stop()


class MUDSlingProcess(protocol.ProcessProtocol):
    alive = False

    def __init__(self, name, plugin, args):
        self.name = name
        self.plugin = plugin
        self.args = args

    def connectionMade(self):
        self.alive = True
        code = [
            "from sys import argv",
            "from runner import run_app",
            "argv[1:] = %r" % self.args,
            "run_app('%s')" % self.plugin,
        ]
        self.transport.write('\n'.join(code))
        self.transport.closeStdin()

    def outReceived(self, data):
        print 'out:', data

    def errReceived(self, data):
        sys.stderr.write(data)

    def processExited(self, reason):
        self.alive = False
        print self.plugin, "exit:", reason

    def processEnded(self, reason):
        print self.plugin, "end:", reason
        process_ended(self.name, reason)


if __name__ == '__main__':
    src = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')

    if '--debugger' in sys.argv:
        sys.argv = sys.argv[1:]
        sys.path.insert(0, src)
        import runner
        runner.run_app('mudsling-server')
    else:
        args = sys.argv[1:]
        processes.update({
            'server': MUDSlingProcess('server', 'mudsling-server', args),
            'proxy': MUDSlingProcess('proxy', 'mudsling-proxy', args),
        })
        for name, process in processes.iteritems():
            print "Spawning %s..." % name
            reactor.spawnProcess(process,
                                 executable=sys.executable,
                                 args=[sys.executable],
                                 env=os.environ,
                                 path=src)
        reactor.run()
