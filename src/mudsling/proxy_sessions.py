from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.protocols import amp
from twisted.internet import reactor
from twisted.internet import defer

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

    def __init__(self, id, ip, delim):
        self.ip = ip
        self.hostname = ip  # Until we resolve it.
        self.line_delimiter = delim
        self.proxy_session_id = id
        proxy_sessions[id] = self
        self.input_buffer = []

    def call_remote(self, *args, **kwargs):
        kwargs['sessId'] = self.proxy_session_id
        d = self.amp.callRemote(*args, **kwargs).addErrback(self.amp._on_error)
        return d

    def raw_send_output(self, text):
        chunks = message_chunks(text)
        nchunks = len(chunks)
        calls = [self.call_remote(ServerToProxy, nchunks=nchunks, chunk=chunk)
                 for chunk in chunks]
        return defer.DeferredList(calls)

    def receive_multipart_input(self, nchunks, chunk):
        if nchunks > 1:
            self.input_buffer.append(chunk)
            if len(self.input_buffer) < nchunks:
                return
            else:
                line = ''.join(self.input_buffer)
                self.input_buffer = []
        else:
            line = chunk
        self.receive_input(line)

    def disconnect(self, reason):
        self.send_output(reason)
        self.call_remote(EndSession)

    def attach_to_player(self, player, report=True):
        super(ProxySession, self).attach_to_player(player)
        if report:
            player_id = player.id if self.game.db.is_valid(player) else -1
            self.call_remote(AttachPlayer, playerId=player_id)


class SetUptime(amp.Command):
    arguments = [
        ('start_time', amp.Float()),
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class NewSession(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('ip', amp.String()),
        ('delim', amp.String()),
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class SetHostname(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('hostname', amp.String()),
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
        ('ip', amp.String()),
        ('hostname', amp.String()),
        ('delim', amp.String()),
        ('playerId', amp.Integer()),
        ('time_connected', amp.Integer()),
        ('last_activity', amp.Float()),
        ('mxp', amp.Boolean())
    ]
    response = []
    errors = {Exception: 'EXCEPTION'}


class SessionOption(amp.Command):
    arguments = [
        ('sessId', amp.Integer()),
        ('optName', amp.String()),
        ('optVal', amp.Integer())
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
        reactor.addSystemEventTrigger('before', 'shutdown', self._on_shutdown)

    def _on_shutdown(self):
        if self.factory.game.exit_code != 10:
            self.callRemote(Shutdown).addErrback(self._on_error)
        self.transport.loseConnection()

    def _on_error(self, error):
        error.trap(Exception)
        # print 'AMPServerProtocol', dir(error)
        error.printDetailedTraceback()

    @SetUptime.responder
    def set_uptime(self, start_time):
        self.factory.game.start_time = start_time
        return {}

    @NewSession.responder
    def new_session(self, sessId, ip, delim):
        session = ProxySession(sessId, ip, delim)
        session.game = self.factory.game
        session.open_session()
        return {}

    @SetHostname.responder
    def set_hostname(self, sessId, hostname):
        try:
            session = proxy_sessions[sessId]
        except KeyError:
            raise InvalidSession()
        session.hostname = hostname
        return {}

    @EndSession.responder
    def end_session(self, sessId):
        try:
            session = proxy_sessions[sessId]
            del proxy_sessions[sessId]
        except KeyError:
            return {}
        session.session_closed()
        return {}

    @ProxyToServer.responder
    def proxy_to_server(self, sessId, nchunks, chunk):
        try:
            session = proxy_sessions[sessId]
        except KeyError:
            raise InvalidSession()
        session.receive_multipart_input(nchunks, chunk)
        return {}

    @ReSyncSession.responder
    def resync_session(self, sessId, ip, hostname, delim, playerId,
                       time_connected, last_activity, mxp):
        """
        Create a server session that corresponds to an already-established
        session on the proxy-side.
        """
        session = ProxySession(sessId, ip, delim)
        session.hostname = hostname
        session.last_activity = last_activity
        session.mxp = mxp
        session.game = self.factory.game
        session.open_session(resync=True)
        session.time_connected = time_connected
        player = session.game.db.get_ref(playerId)
        if player.is_valid():
            session.attach_to_player(player)
        else:
            self.factory.game.login_screen.session_connected(session)
        return {}

    @SessionOption.responder
    def session_option(self, sessId, optName, optVal):
        try:
            session = proxy_sessions[sessId]
        except KeyError:
            raise InvalidSession()
        session.set_option(optName, optVal)
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
