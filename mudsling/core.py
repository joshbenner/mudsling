"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
import os
import cPickle as pickle
import atexit

# Prefer libs we ship with.
libpath = os.path.join(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))), "lib")
sys.path.insert(1, libpath)

import ConfigParser
import logging

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
sys.modules['configparser'] = sys.modules['ConfigParser']

from twisted.application.service import Service
from twisted.application.service import IServiceCollection

from mudsling.extensibility import PluginManager
from mudsling.sessions import SessionHandler
from mudsling.storage import Database
from mudsling.utils.modules import class_from_path

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
    db_file_path = ""

    #: @type: SessionHandler
    session_handler = None

    #: @type: mudsling.plugins.LoginScreenPlugin
    login_screen = None

    #: @type: types.ClassType
    player_class = None
    character_class = None
    room_class = None

    def __init__(self, game_dir="game", app=None):
        # Populated by service.setServiceParent().
        self.services = IServiceCollection(app)

        self.game_dir = game_dir

        self.initGameDir()

        # Load configuration.
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(self.configPaths())

        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(self, game_dir)

        # Parse class configs and stash class refs on the game object.
        self.loadClassConfigs()

        self.loadDatabase()
        atexit.register(self.saveDatabase)

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

    def initGameDir(self):
        """
        If game dir doesn't exist, try to create it.
        """
        if not os.path.exists(self.game_dir):
            logging.info("Creating game directory %s"
                         % os.path.realpath(self.game_dir))
            os.makedirs(self.game_dir)
            if os.path.exists(self.game_dir):
                f = open(os.path.join(self.game_dir, 'settings.cfg'), 'w')
                f.close()
        elif not os.path.isdir(self.game_dir):
            raise Exception("Game dir is a file!")

    def loadClassConfigs(self):
        """
        Cycle through the [Classes] config section, finding the configured
        classes, making sure their modules are loaded and the game has a ref
        to the class object.
        """
        for config_name, class_path in self.config.items('Classes'):
            attrname = config_name.replace(' ', '_')
            setattr(self, attrname, class_from_path(class_path))

    def loadDatabase(self):
        dbfilename = self.config.get('Main', 'db file')
        self.db_file_path = os.path.join(self.game_dir, dbfilename)
        if os.path.exists(self.db_file_path):
            logging.info("Loading database from %s" % self.db_file_path)
            dbfile = open(self.db_file_path, 'rb')
            self.db = pickle.load(dbfile)
            dbfile.close()
            self.db.onLoaded()
        else:
            logging.info("Initializing new database at %s" % self.db_file_path)
            self.db = Database()
            self.db.onLoaded()

            # Create first player.
            #: @type: mudsling.objects.BasePlayer
            player = self.player_class('admin', 'password', 'admin@localhost')
            self.db.registerNewObject(player)

            #: @type: mudsling.objects.BaseCharacter
            char = self.db.createObject(self.character_class, 'Admin')
            char.possessable_by.append(player)

            player.possessObject(char)

            #: @type: mudsling.topography.Room
            room = self.db.createObject(self.room_class, "The First Room")

            char.moveTo(room)

            self.invokeHook('initDatabase', self.db)

            # Get the db on disk.
            self.saveDatabase()

    def saveDatabase(self):
        with open(self.db_file_path, 'wb') as dbfile:
            pickle.dump(self.db, dbfile, -1)

    def invokeHook(self, hook, *args, **kwargs):
        """
        Invoke an arbitrary hook on all activated GamePlugins.

        These hooks are intended for system- and game-wide events and should
        not be used for object-specific events.

        @param hook: The hook (function) to execute.
        @param args: Positional args to pass to the hook.
        @param kwargs: Keyword args to pass to the hook.
        @return: Dictionary of hook results keyed by plugin info.
        @rtype: dict
        """
        hook = "hook_" + hook
        return self.plugins.invokeHook('GamePlugin', hook, *args, **kwargs)
