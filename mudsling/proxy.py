from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.protocols import amp

from mudsling.sessions import Session

proxy_sessions = {}


class InvalidSession(Exception):
    pass


class ProxySession(Session):
    """
    A server-side session that is coming in via the Proxy AMP channel.

    @cvar amp: Reference to the active AMP protocol session with proxy.

    @ivar proxy_session_id: The ID that associates this instance with the
        corresponding instance in the Proxy process.
    """
    amp = None  # Set by AMPServerProtocol upon instantiation (connection).
    proxy_session_id = None

    def __init__(self, id, delim):
        self.line_delimiter = delim
        self.proxy_session_id = id
        proxy_sessions[id] = self

    def rawSendOutput(self, text):
        self.amp.callRemote(ServerToProxy, sessId=self.proxy_session_id,
                            text=text).addErrback(self.amp.errInvalidSession)


class NewSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('delim', amp.String())
    ]
    response = []


class EndSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer())
    ]
    response = []


class ProxyToServer(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('line', amp.String())
    ]
    response = []
    errors = {InvalidSession: 'INVALID_SESSION'}


class ServerToProxy(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('text', amp.String())
    ]
    response = []
    errors = {InvalidSession: 'INVALID_SESSION'}


class AMPServerProtocol(amp.AMP):
    factory = None

    def __init__(self):
        super(AMPServerProtocol, self).__init__()
        ProxySession.amp = self

    def errInvalidSession(self, error):
        error.trap(InvalidSession)
        print 'AMPServerProtocol', error.__dict__

    @NewSession.responder
    def newSession(self, sessId, delim):
        session = ProxySession(sessId, delim)
        session.game = self.factory.game
        session.openSession()
        return {}

    @EndSession.responder
    def endSession(self, sessId):
        try:
            session = proxy_sessions[sessId]
            del proxy_sessions[sessId]
        except KeyError:
            return {}
        session.sessionClosed()
        return {}

    @ProxyToServer.responder
    def proxyToServer(self, sessId, line):
        try:
            session = proxy_sessions[sessId]
        except KeyError:
            raise InvalidSession()
        session.receiveInput(line)
        return {}


def AMP_server(game, port):
    factory = ServerFactory()
    factory.protocol = AMPServerProtocol
    factory.game = game
    service = internet.TCPServer(port, factory)
    service.setName("AMPServer")
    return service
