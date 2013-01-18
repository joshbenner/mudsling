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
        factory.game = self.game
        service = internet.TCPServer(self.port, factory)
        service.setName("SimpleTelnetServer")
        return service


class SimpleTelnetSession(StatefulTelnetProtocol, Session):

    #: @ivar: Will be set by factory when Session instance is spawned.
    #: @type: ServerFactory
    factory = None

    def connectionMade(self):
        self.game = self.factory.game
        self.initSession()
        if self.line_delimiter != self.delimiter:
            self.line_delimiter = self.delimiter

    def connectionLost(self, reason):
        self.closeSession()

    def lineReceived(self, line):
        """
        LineReceiver (part of StatefulTelnetProtocol) calls this when a line of
        input is received from the client. We let the Session side of things
        handle this.
        """
        self.receiveInput(line)

    def rawSendOutput(self, text):
        """
        Overrides Session.rawSendOutput() so we can forward the line via the
        protocol.
        """
        self.transport.write(text)
