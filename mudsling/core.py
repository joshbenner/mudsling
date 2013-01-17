"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
from os import path

# Prefer libs we ship with.
sys.path.insert(1, path.join(path.dirname(path.realpath(__file__)), "lib"))

import ConfigParser
import logging

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
sys.modules['configparser'] = sys.modules['ConfigParser']

from twisted.application.service import Service
from twisted.application.service import IServiceCollection

from mudsling.plugins import PluginManager

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

    #: @type: mudsling.storage.Database
    db = None

    def __init__(self, game_dir="game", app=None):
        # Populated by service.setServiceParent().
        self.services = IServiceCollection(app)

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
                service.setServiceParent(app)

    def config_paths(self):
        """
        Get a list of paths to files where configuration might be found.
        """
        return ["mudsling/defaults.cfg", "%s/settings.cfg" % self.game_dir]


