import sys
import ConfigParser
import logging

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
sys.modules['configparser'] = sys.modules['ConfigParser']

from twisted.application.service import Application, Service
from twisted.application.service import IServiceCollection

from mudsling.config.PluginManager import PluginManager

logging.basicConfig(level=logging.DEBUG)


class MUDSling(object):

    #: @type: str
    game_dir = "game"

    #: @type: ConfigParser.SafeConfigParser
    config = None

    #: @type: PluginManager
    plugins = None

    #: @type: IServiceCollection
    services = None

    def __init__(self, game_dir="game"):
        application = Application("MUDSling Game Server")
        self.services = IServiceCollection(application)

        self.game_dir = game_dir

        # Load configuration.
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(self.config_paths())

        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(game_dir, self.config)

        # Gather Twisted services and register them to our application.
        for info in self.plugins.active_plugins("TwistedService"):
            service = info.plugin_object.get_service()
            if isinstance(service, Service):
                service.setServiceParent(application)

    def config_paths(self):
        """
        Get a list of paths to files where configuration might be found.
        """
        return ["mudsling/defaults.cfg", "%s/settings.cfg" % self.game_dir]
