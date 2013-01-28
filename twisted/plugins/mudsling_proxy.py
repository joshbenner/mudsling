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
from twisted.protocols.amp import AMP

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
        factory.protocol = AmpClientProtocol
        client = internet.TCPClient('127.0.0.1', port, factory)
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
    player = None
    amp = None  # Set by AmpClientProtocol on class when it is instantiated.

    def __init__(self):
        self.session_id = session_id()
        sessions[self.session_id] = self

    def callRemote(self, *args, **kwargs):
        kwargs['sessId'] = self.session_id
        return self.amp.callRemote(*args, **kwargs)

    def connectionMade(self):
        self.callRemote(proxy.NewSession, delim=self.delimiter)

    def connectionLost(self, reason):
        self.callRemote(proxy.EndSession)

    def lineReceived(self, line):
        self.callRemote(proxy.ProxyToServer,
                        line=line).addErrback(self.amp.errInvalidSession)


class AmpClientProtocol(AMP):
    def __init__(self):
        super(AmpClientProtocol, self).__init__()
        ProxyTelnetSession.amp = self

    def errInvalidSession(self, error):
        error.trap(proxy.InvalidSession)
        print error.__dict__

    @proxy.ServerToProxy.responder
    def serverToProxy(self, sessId, text):
        try:
            session = sessions[sessId]
        except KeyError:
            raise proxy.InvalidSession(str(sessId))
        session.transport.write(text)
        return {}


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingProxyServiceMaker()
