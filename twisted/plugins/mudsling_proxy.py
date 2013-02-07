import os
import sys
import imp
import ConfigParser

modulepath = os.path.dirname(os.path.realpath(__file__))
options_module = imp.load_source('options',
                                 os.path.join(modulepath, 'options.py'))
Options = options_module.Options

from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application.service import MultiService
from twisted.conch.telnet import StatefulTelnetProtocol
from twisted.internet.protocol import ServerFactory, ReconnectingClientFactory
from twisted.application import internet
from twisted.protocols import amp
from twisted.internet import reactor

from mudsling import proxy


max_session_id = 0
sessions = {}


def session_id():
    sys.modules[__name__].max_session_id += 1
    return max_session_id


class MUDSlingProxyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "mudsling-proxy"
    description = "The MUDSling proxy service."
    options = Options

    def makeService(self, options):
        service = MultiService()

        config = ConfigParser.SafeConfigParser()
        config.read(options.configPaths())

        port = int(config.get('Proxy', 'AMP port'))
        factory = ReconnectingClientFactory()
        factory.maxDelay = 1
        factory.protocol = AmpClientProtocol
        client = internet.TCPClient('127.0.0.1', port, factory)
        client.setName('main')  # Used by AppRunner to find exit code.
        service.addService(client)

        ports_str = config.get('Proxy', 'telnet ports')
        for portVal in ports_str.split(','):
            try:
                port = int(portVal)
            except ValueError:
                continue
            factory = ServerFactory()
            factory.protocol = ProxyTelnetSession
            child = internet.TCPServer(port, factory)
            child.setName("ProxyTelnet%d" % port)
            service.addService(child)

        return service


class ProxyTelnetSession(StatefulTelnetProtocol):
    factory = None

    session_id = None
    time_connected = 0
    playerId = None
    amp = None  # Set by AmpClientProtocol on class when it is instantiated.

    output_buffer = []

    def __init__(self):
        self.session_id = session_id()
        sessions[self.session_id] = self
        self.output_buffer = []
        self.MAX_LENGTH = amp.MAX_VALUE_LENGTH * 8

    def callRemote(self, *args, **kwargs):
        kwargs['sessId'] = self.session_id
        self.amp.callRemote(*args, **kwargs).addErrback(self.amp._onError)

    def connectionMade(self):
        # If not in session list, then disconnect may have originated on the
        # server side, or there is some very fast disconnect.
        if self.session_id in sessions:
            self.callRemote(proxy.NewSession, delim=self.delimiter)

    def connectionLost(self, reason):
        self.callRemote(proxy.EndSession)

    def lineReceived(self, line):
        parts = proxy.message_chunks(line)
        for part in parts:
            self.callRemote(proxy.ProxyToServer,
                            nchunks=len(parts),
                            chunk=part)

    def receiveMultipartOutput(self, nchunks, chunk):
        if nchunks > 1:
            self.output_buffer.append(chunk)
            if len(self.output_buffer) < nchunks:
                return
            else:
                text = ''.join(self.output_buffer)
                self.output_buffer = []
        else:
            text = chunk
        self.transport.write(text)

    def disconnect(self):
        print "Closing proxy telnet session %d" % self.session_id
        try:
            del sessions[self.session_id]
        except KeyError:
            pass
        self.transport.loseConnection()

    def reSync(self):
        self.callRemote(proxy.ReSyncSession,
                        delim=self.delimiter,
                        playerId=self.playerId,
                        time_connected=self.time_connected)


class AmpClientProtocol(amp.AMP):
    def __init__(self):
        super(AmpClientProtocol, self).__init__()
        ProxyTelnetSession.amp = self

    def connectionMade(self):
        self.factory.resetDelay()
        # If we already have telnet sessions up connect, it's because the
        # server restarted, and we need to re-establish sessions via AMP.
        for session in sessions.itervalues():
            session.reSync()

    def _onError(self, error):
        error.trap(Exception)
        print 'AmpClientProtocol', error.__dict__

    @proxy.ServerToProxy.responder
    def serverToProxy(self, sessId, nchunks, chunk):
        try:
            session = sessions[sessId]
        except KeyError:
            raise proxy.InvalidSession(str(sessId))
        #session.transport.write(chunk)
        session.receiveMultipartOutput(nchunks, chunk)
        return {}

    @proxy.Shutdown.responder
    def shutdownProxy(self):
        print "Proxy received Shutdown signal from server"
        reactor.stop()
        return {}

    @proxy.EndSession.responder
    def endSession(self, sessId):
        try:
            session = sessions[sessId]
        except KeyError:
            raise proxy.InvalidSession(str(sessId))
        session.disconnect()
        return {}

    @proxy.AttachPlayer.responder
    def attachPlayer(self, sessId, playerId):
        try:
            session = sessions[sessId]
        except KeyError:
            raise proxy.InvalidSession(str(sessId))
        session.playerId = playerId
        return {}


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingProxyServiceMaker()