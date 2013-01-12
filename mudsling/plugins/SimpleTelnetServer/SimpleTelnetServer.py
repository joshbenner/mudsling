from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.conch.telnet import TelnetTransport
from twisted.internet.protocol import ServerFactory
from twisted.application import internet

from mudsling.config.plugins import ITwistedServicePlugin


class SimpleTelnetServer(ITwistedServicePlugin):

    port = 4000

    def activate(self):
        super(SimpleTelnetServer, self).activate()
        if 'port' in self.options:
            self.port = self.options['port']

    def get_service(self):
        factory = ServerFactory()
        factory.protocol = SimpleTelnetProtocol
        service = internet.TCPServer(self.port, factory)
        service.setName("SimpleTelnetServer")
        return service


class SimpleTelnetProtocol(StatefulTelnetProtocol):
    def lineReceived(self, line):
        print "Received %s" % line
