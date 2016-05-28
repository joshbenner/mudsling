from twisted.conch.telnet import Telnet, StatefulTelnetProtocol
from twisted.protocols import basic
from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.internet.defer import Deferred

from mudsling.extensibility import TwistedServicePlugin
from mudsling.sessions import Session
from mudsling.utils.string import mxp


class SimpleTelnetServer(TwistedServicePlugin):
    def get_service(self):
        factory = ServerFactory()
        factory.protocol = SimpleTelnetSession
        factory.game = self.game
        service = internet.TCPServer(self.options.getint('port'), factory)
        service.setName("SimpleTelnetServer")
        return service


class SimpleTelnetSession(Telnet, basic.LineReceiver, Session):

    #: @ivar: Will be set by factory when Session instance is spawned.
    #: @type: ServerFactory
    factory = None
    delimiter = '\n'

    def connectionMade(self):
        self.game = self.factory.game
        self.open_session()

    def attach_to_player(self, player):
        super(SimpleTelnetSession, self).attach_to_player(player)
        self.negotiate_mxp()

    def connectionLost(self, reason):
        self.session_closed()

    def applicationDataReceived(self, bytes):
        basic.LineReceiver.dataReceived(self, bytes)

    def lineReceived(self, line):
        """
        LineReceiver calls this when a line of input is received from the
        client. We let the Session side of things handle this.
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

    def enableRemote(self, option):
        return False

    def enableLocal(self, option):
        if option == mxp.TELNET_OPT:
            self.set_option('mxp', True)
            return True
        return False

    def disableLocal(self, option):
        if option == mxp.TELNET_OPT:
            self.set_option('mxp', False)
            return True
        return False

    def negotiate_mxp(self):
        def enable_mxp(opt):
            self.requestNegotiation(mxp.TELNET_OPT, '')

        def no_mxp(opt):
            pass

        return self.will(mxp.TELNET_OPT).addCallbacks(enable_mxp, no_mxp)
