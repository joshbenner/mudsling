from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.protocols import amp
from twisted.internet import reactor

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

    input_buffer = []

    def __init__(self, id, delim):
        self.line_delimiter = delim
        self.proxy_session_id = id
        proxy_sessions[id] = self
        self.input_buffer = []

    def rawSendOutput(self, text):
        chunks = message_chunks(text)
        for chunk in chunks:
            call = self.amp.callRemote(ServerToProxy,
                                       sessId=self.proxy_session_id,
                                       nchunks=len(chunks),
                                       chunk=chunk)
            call.addErrback(self.amp._onError)

    def receiveMultipartInput(self, nchunks, chunk):
        if nchunks > 1:
            self.input_buffer.append(chunk)
            if len(self.input_buffer) < nchunks:
                return
            else:
                line = ''.join(self.input_buffer)
                self.input_buffer = []
        else:
            line = chunk
        self.receiveInput(line)

    def disconnect(self, reason):
        self.sendOutput(reason)
        call = self.amp.callRemote(EndSession, sessId=self.proxy_session_id)
        call.addErrback(self.amp._onError)


class NewSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('delim', amp.String())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class EndSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class ProxyToServer(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('nchunks', amp.Integer()),
        ('chunk', amp.String())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class ServerToProxy(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('nchunks', amp.Integer()),
        ('chunk', amp.String())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class Shutdown(amp.Command):
    arguments = []
    response = []
    errors = {Exception: 'EXCEPTION'}


class AMPServerProtocol(amp.AMP):
    factory = None

    def __init__(self):
        super(AMPServerProtocol, self).__init__()
        ProxySession.amp = self
        reactor.addSystemEventTrigger('before', 'shutdown', self._onShutdown)

    def _onShutdown(self):
        if self.factory.game.exit_code != 10:
            self.callRemote(Shutdown).addErrback(self._onError)

    def _onError(self, error):
        error.trap(Exception)
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
    def proxyToServer(self, sessId, nchunks, chunk):
        try:
            session = proxy_sessions[sessId]
        except KeyError:
            raise InvalidSession()
        session.receiveMultipartInput(nchunks, chunk)
        return {}


def message_chunks(text):
    return [text[i:i + amp.MAX_VALUE_LENGTH]
            for i in range(0, len(text), amp.MAX_VALUE_LENGTH)]


def AMP_server(game, port):
    factory = ServerFactory()
    factory.protocol = AMPServerProtocol
    factory.game = game
    service = internet.TCPServer(port, factory)
    service.setName("AMPServer")
    return service
