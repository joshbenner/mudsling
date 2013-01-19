"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
import os

# Prefer libs we ship with.
libpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib")
sys.path.insert(1, libpath)

import ConfigParser
import logging

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
sys.modules['configparser'] = sys.modules['ConfigParser']

from twisted.application.service import Service
from twisted.application.service import IServiceCollection

from mudsling.extensibility import PluginManager
from mudsling.sessions import SessionHandler

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

    #: @type: SessionHandler
    session_handler = None

    #: @type: mudsling.plugins.LoginScreenPlugin
    login_screen = None

    def __init__(self, game_dir="game", app=None):
        # Populated by service.setServiceParent().
        self.services = IServiceCollection(app)

        self.game_dir = game_dir

        # Load configuration.
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(self.configPaths())

        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(self, game_dir)

        # Setup session handler. Used by services.
        self.session_handler = SessionHandler(self)

        # Setup the plugin handling the login screen.
        name = self.config.get('Main', 'login screen')
        plugin = self.plugins.getPluginByMachineName(name, "LoginScreen")
        if plugin is not None:
            logging.debug("Using %s as LoginScreen" % name)
            self.login_screen = plugin.plugin_object

        # Gather Twisted services and register them to our application.
        for info in self.plugins.activePlugins("TwistedService"):
            service = info.plugin_object.get_service()
            if isinstance(service, Service):
                service.setServiceParent(app)

    def configPaths(self):
        """
        Get a list of paths to files where configuration might be found.
        """
        return ["mudsling/defaults.cfg", "%s/settings.cfg" % self.game_dir]
