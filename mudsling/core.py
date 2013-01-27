"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
import os
import cPickle as pickle
import atexit

# Prefer libs we ship with.
basepath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
libpath = os.path.join(basepath, "lib")
sys.path.insert(1, libpath)
del basepath, libpath

import ConfigParser
import logging

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
sys.modules['configparser'] = sys.modules['ConfigParser']

from twisted.internet import reactor
from twisted.application.service import Service
#from twisted.application.service import IServiceCollection

from mudsling.extensibility import PluginManager
from mudsling.sessions import SessionHandler
from mudsling.storage import Database
from mudsling.utils.modules import class_from_path

logging.basicConfig(level=logging.DEBUG)


class MUDSling(object, Service):
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

    class_registry = {}

    def __init__(self):
        # Set this name so our AppRunner can find the primary service and
        # capture the exit code.
        self.setName("main")

        # Populated by service.setServiceParent().
        #self.services = IServiceCollection(app)

        #self.game_dir = game_dir

        self.initGameDir()

        # Load configuration.
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(self.configPaths())

        logging.debug('\n'.join(sys.path))

        # Setup session handler. Used by services.
        self.session_handler = SessionHandler(self)

    def startService(self):
        Service.startService(self)
        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(self, self.game_dir)

        self.loadClassConfigs()
        self.buildClassRegistry()
        self.loadDatabase()
        atexit.register(self.saveDatabase)

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
                service.setServiceParent(self.parent)

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
            #: @type: Database
            self.db = pickle.load(dbfile)
            dbfile.close()
            self.db.onLoaded(self)
        else:
            logging.info("Initializing new database at %s" % self.db_file_path)
            self.db = Database()
            self.db.onLoaded(self)

            # Create first player.
            #: @type: mudsling.objects.BasePlayer
            player = self.db.createObject(self.player_class, 'admin')
            player.setPassword('pass')
            player.email = 'admin@localhost'
            player.superuser = True

            #: @type: mudsling.objects.BaseCharacter
            char = self.db.createObject(self.character_class, 'Admin')
            char.possessable_by.append(player)

            player.default_object = char
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

    def exit(self, code=0):
        reactor.stop()
        self.exit_code = code

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

    def buildClassRegistry(self):
        """
        Builds a class registry for all classes which can be @create'd in-game.
        We do this so that we can have friendly names and easily produce lists
        of object types.

        The MUDSling server doesn't register its base classes; however, some
        classes are registered by the MUDSlingCore default plugin.

        Invokes hook_objectClasses and expects responding plugins to return a
        list of (name, class) tuples.
        """
        self.class_registry = {}
        for plugin, response in self.invokeHook('objectClasses').iteritems():
            if not isinstance(response, list):
                continue
            try:
                for name, cls in response:
                    if name in self.class_registry:
                        logging.error("Duplicate class name: %s" % name)
                        alt = cls.__module__ + '.' + cls.__name__
                        self.class_registry[alt] = cls
                    else:
                        self.class_registry[name] = cls
            except TypeError:
                err = "Invalid class registration from %s" % plugin.name
                logging.error(err)

    def getClass(self, name):
        """
        Searches the class registry for a class matching the given name.
        @param name: The class name to search for.
        @return: The class with the specified pretty name.
        @rtype: type or None
        """
        if name in self.class_registry:
            return self.class_registry[name]
        return None

    def getClassName(self, cls):
        """
        Given a class, find the class registry name that corresponds to it.
        @param cls: The class whose pretty name to retrieve.
        @return: The pretty name of the class.
        @rtype: str or None
        """
        for name, obj in self.class_registry.iteritems():
            if obj == cls:
                return name
        return None
