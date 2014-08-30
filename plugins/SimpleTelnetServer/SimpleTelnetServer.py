from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.internet.defer import Deferred

from mudsling.extensibility import TwistedServicePlugin
from mudsling.sessions import Session


class SimpleTelnetServer(TwistedServicePlugin):
    def get_service(self):
        factory = ServerFactory()
        factory.protocol = SimpleTelnetSession
        factory.game = self.game
        service = internet.TCPServer(self.options.getint('port'), factory)
        service.setName("SimpleTelnetServer")
        return service


class SimpleTelnetSession(StatefulTelnetProtocol, Session):

    #: @ivar: Will be set by factory when Session instance is spawned.
    #: @type: ServerFactory
    factory = None

    def connectionMade(self):
        self.game = self.factory.game
        self.open_session()

    def connectionLost(self, reason):
        self.session_closed()

    def lineReceived(self, line):
        """
        LineReceiver (part of StatefulTelnetProtocol) calls this when a line of
        input is received from the client. We let the Session side of things
        handle this.
        """
        self.receive_input(line)

    def raw_send_output(self, text):
        """
        Overrides Session.raw_send_output() so we can forward the line via the
        protocol.
        """
        self.transport.write(text)
        return Deferred()

    def disconnect(self, reason):
        self.send_output(reason)
        self.transport.loseConnection()
