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

    def callRemote(self, *args, **kwargs):
        kwargs['sessId'] = self.proxy_session_id
        self.amp.callRemote(*args, **kwargs).addErrback(self.amp._onError)

    def rawSendOutput(self, text):
        chunks = message_chunks(text)
        for chunk in chunks:
            self.callRemote(ServerToProxy,
                            nchunks=len(chunks),
                            chunk=chunk)

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
        self.callRemote(EndSession)

    def attachToPlayer(self, player, report=True):
        super(ProxySession, self).attachToPlayer(player)
        if report:
            player_id = player.id if self.game.db.isValid(player) else -1
            self.callRemote(AttachPlayer, playerId=player_id)


class NewSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('delim', amp.String()),
        ('mxp', amp.Boolean())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class AttachPlayer(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('playerId', amp.Integer())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class ReSyncSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('delim', amp.String()),
        ('playerId', amp.Integer()),
        ('time_connected', amp.Integer()),
        ('mxp', amp.Boolean())
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
    def newSession(self, sessId, delim, mxp):
        session = ProxySession(sessId, delim)
        session.mxp = mxp
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

    @ReSyncSession.responder
    def reSyncSession(self, sessId, delim, playerId, time_connected, mxp):
        """
        Create a server session that corresponds to an already-established
        session on the proxy-side.
        """
        session = ProxySession(sessId, delim)
        session.mxp = mxp
        session.game = self.factory.game
        session.openSession(resync=True)
        session.time_connected = time_connected
        player = session.game.db.getRef(playerId)
        if player.isValid():
            session.attachToPlayer(player)
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
