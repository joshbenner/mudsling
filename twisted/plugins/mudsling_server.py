from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from mudsling.core import MUDSling


class Options(usage.Options):
    optFlags = [["debugger", "d", "Run in debugger-compatibility mode."]]


class MUDSlingServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "mudsling"
    description = "The MUDSling game service."
    options = Options

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in myproject.
        """
        game = MUDSling()
        if options['debugger']:
            game.config.set('Plugins', 'SimpleTelnetServer', 'Enabled')
        return game


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingServiceMaker()
