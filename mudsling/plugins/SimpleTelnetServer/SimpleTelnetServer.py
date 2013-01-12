from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.internet.protocol import ServerFactory
from twisted.application import internet

from mudsling.config.plugins import ITwistedServicePlugin
from mudsling.net.sessions import Session


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


class SimpleTelnetProtocol(StatefulTelnetProtocol, Session):
    def connectionMade(self):
        self.init_session()

    def lineReceived(self, line):
        """
        LineReceiver (part of StatefulTelnetProtocol) calls this when a line of
        input is received from the client. We let the Session side of things
        handle this.
        """
        self.receive_input(line)

    def _send_line(self, line):
        """
        Overrides Session._send_line() so we can forward the line via the
        protocol.
        """
        self.sendLine(line)
