import os
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


class MUDSlingProxyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "mudsling-proxy"
    description = "The MUDSling proxy service."
    options = Options

    def makeService(self, options):
        service = MultiService()

        config = ConfigParser.SafeConfigParser()
        config.read(options.configPaths())
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

        port = int(config.get('Proxy', 'AMP port'))
        factory = ReconnectingClientFactory()
        factory.protocol = AmpClientProtocol
        client = internet.TCPClient('127.0.0.1', port, factory)
        service.addService(client)

        return service


class ProxyTelnetSession(StatefulTelnetProtocol):
    pass


class AmpClientProtocol(AMP):
    pass


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingProxyServiceMaker()
