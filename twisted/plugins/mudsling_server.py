import os
import imp

modulepath = os.path.dirname(os.path.realpath(__file__))
options_module = imp.load_source('options',
                                 os.path.join(modulepath, 'options.py'))
Options = options_module.Options

from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from mudsling.core import MUDSling


class MUDSlingServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "mudsling-server"
    description = "The MUDSling game service."
    options = Options

    def makeService(self, options):
        game = MUDSling(options['gamedir'], options.configPaths())
        game.setName('main')  # Used by AppRunner to find exit code
        if options['debugger']:
            game.config.set('Plugins', 'SimpleTelnetServer', 'Enabled')
            game.config.set('Proxy', 'enabled', 'No')
        return game


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MUDSlingServiceMaker()