from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.internet.protocol import ServerFactory
from twisted.application import internet

from mudsling.plugins import TwistedServicePlugin
from mudsling.sessions import Session


class SimpleTelnetServer(TwistedServicePlugin):

    port = 4000

    def activate(self):
        super(SimpleTelnetServer, self).activate()
        if 'port' in self.options:
            self.port = self.options['port']

    def get_service(self):
        factory = ServerFactory()
        factory.protocol = SimpleTelnetSession
        service = internet.TCPServer(self.port, factory)
        service.setName("SimpleTelnetServer")
        return service


class SimpleTelnetSession(StatefulTelnetProtocol, Session):

    #: @ivar: Will be set by factory when Session instance is spawned.
    #: @type: ServerFactory
    factory = None

    def connectionMade(self):
        self.init_session()

    def connectionLost(self, reason):
        self.close_session()

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
