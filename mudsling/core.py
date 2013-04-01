"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
import os
import cPickle as pickle

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
from twisted.application.service import Service, MultiService

from mudsling.extensibility import PluginManager
from mudsling.sessions import SessionHandler
from mudsling.storage import Database
from mudsling.objects import BasePlayer
from mudsling import proxy
from mudsling import tasks
from mudsling import registry
from mudsling import locks
from mudsling import lockfuncs

from mudsling import utils
import mudsling.utils.modules
import mudsling.utils.time
import mudsling.utils.sequence

logging.basicConfig(level=logging.DEBUG)


class MUDSling(MultiService):
    #: @type: C{str}
    game_dir = "game"

    #: @type: L{ConfigParser.SafeConfigParser}
    config = None

    #: @type: L{PluginManager}
    plugins = None

    #: @type: L{mudsling.storage.Database}
    db = None
    db_file_path = ""

    #: @type: L{SessionHandler}
    session_handler = None

    #: @type: L{mudsling.plugins.LoginScreenPlugin}
    login_screen = None

    #: @type: C{types.ClassType}
    player_class = None
    character_class = None
    room_class = None

    def __init__(self, gameDir, configPaths):
        """
        @type gameDir: C{str}
        @type configPaths: C{list}
        """
        MultiService.__init__(self)

        self.game_dir = gameDir
        self.initGameDir()

        # Load configuration.
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(configPaths)

    def initGame(self):
        logging.info("Initializing game...")
        # Setup session handler. Used by services.
        self.session_handler = SessionHandler(self)

        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(self, self.game_dir)

        self.initLocks()
        self.loadClassConfigs()
        registry.classes.buildClassRegistry(self)
        self.loadDatabase()

        # Dependency injection.
        tasks.BaseTask.game = self
        tasks.BaseTask.db = self.db

        if not self.db.initialized:
            self.initDatabase()

        # Setup the plugin handling the login screen.
        name = self.config.get('Main', 'login screen')
        plugin = self.plugins.getPluginByMachineName(name, "LoginScreen")
        if plugin is not None:
            logging.debug("Using %s as LoginScreen" % name)
            self.login_screen = plugin.plugin_object

    def startService(self):
        self.initGame()
        logging.info("Starting services...")
        # Gather Twisted services and register them to our application.
        for info in self.plugins.activePlugins("TwistedService"):
            service = info.plugin_object.get_service()
            if isinstance(service, Service):
                #service.setServiceParent(self.parent)
                self.addService(service)

        # Setup the AMP server if we are using proxy.
        if self.config.getboolean('Proxy', 'enabled'):
            service = proxy.AMP_server(self,
                                       self.config.getint('Proxy', 'AMP port'))
            self.addService(service)

        # Fire server startup hooks.
        self.db.onServerStartup()
        self.invokeHook('serverStartup')

        MultiService.startService(self)

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
            setattr(self, attrname, utils.modules.class_from_path(class_path))

    def initLocks(self):
        """
        Gather the lock functions and initialize the lock parser.
        """
        lockFuncs = lockfuncs.defaultFuncs()
        hookResponses = self.invokeHook("lockFunctions")
        lockFuncs.update(utils.sequence.dictMerge(*hookResponses.values()))
        logging.info("Loaded %d lock functions", len(lockFuncs))
        # Initialize the parser. The result is cached in the module for future
        # calls to obtain the parser.
        locks.parser(lockFuncs, reset=True)

    def loadDatabase(self):
        dbfilename = self.config.get('Main', 'db file')
        self.db_file_path = os.path.join(self.game_dir, dbfilename)
        if os.path.exists(self.db_file_path):
            logging.info("Loading database from %s" % self.db_file_path)
            dbfile = open(self.db_file_path, 'rb')
            #: @type: Database
            self.db = pickle.load(dbfile)
            dbfile.close()
        else:
            logging.info("Initializing new database at %s" % self.db_file_path)
            self.db = Database()
        self.db.onLoaded(self)

        # Build the player registry.
        for player in self.db.descendants(BasePlayer):
            registry.players.registerPlayer(player)

    def initDatabase(self):
        self.db.initialized = True

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

        task = CheckpointTask()
        task.start(task.configuredInterval())

        self.invokeHook('initDatabase', self.db)

        # Get the db on disk.
        self.saveDatabase()

    def saveDatabase(self):
        with open(self.db_file_path, 'wb') as dbfile:
            pickle.dump(self.db, dbfile, -1)

    def shutdown(self, reload=False):
        # Call shutdown hooks.
        self.invokeHook('serverShutdown', reload=reload)
        self.db.onServerShutdown()
        self.__exit(10 if reload else 0)

    def reload(self):
        self.shutdown(reload=True)

    def __exit(self, code=0):
        self.exit_code = code
        if code != 10:
            self.session_handler.disconnectAllSessions("Shutting Down")
        self.saveDatabase()
        #noinspection PyUnresolvedReferences
        reactor.stop()

    def invokeHook(self, hook, *args, **kwargs):
        """
        Invoke an arbitrary hook on all activated GamePlugins.

        These hooks are intended for system- and game-wide events and should
        not be used for object-specific events.

        @param hook: The hook (function) to execute.
        @param args: Positional args to pass to the hook.
        @param kwargs: Keyword args to pass to the hook.
        @return: Dictionary of hook results keyed by plugin info.
        @rtype: C{dict}
        """
        hook = "hook_" + hook
        return self.plugins.invokeHook('GamePlugin', hook, *args, **kwargs)


class CheckpointTask(tasks.Task):
    def __str__(self):
        return "The Checkpoint Task"

    def run(self):
        self.game.saveDatabase()

    def configuredInterval(self):
        return utils.time.dhms_to_seconds(
            self.game.config.get('Main', 'checkpoint interval')
        )

    def onServerStartup(self):
        self.restart(self.configuredInterval())
