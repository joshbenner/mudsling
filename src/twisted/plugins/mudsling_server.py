from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from mudsling.options import Options

# These are in path because src is the current dir when the plugin runs.
from mudsling.core import MUDSling
from mudsling.config import config


class MUDSlingServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "mudsling-server"
    description = "The MUDSling game service."
    options = Options

    def makeService(self, options):
        game = MUDSling(options['gamedir'], options.configPaths())
        game.setName('main')  # Used by AppRunner to find exit code
        if options['debugger']:
            config.set('Plugins', 'SimpleTelnetServer', 'Enabled')
            config.set('Proxy', 'enabled', 'No')
        return game


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingServiceMaker()
