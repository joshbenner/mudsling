"""
Main game class that manages the twisted application, configuration, plugins,
services... everything.
"""

import sys
import os
import cPickle as pickle
import logging
import time

from twisted.internet import reactor
from twisted.application.service import Service, MultiService

from mudsling.config import config

# Alias configparser -> ConfigParser for yapsy (Python 3 naming)
# Works best if it comes between config and plugin imports.
sys.modules['configparser'] = sys.modules['ConfigParser']

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
import mudsling.utils.sequence


class MUDSling(MultiService):
    #: @type: C{str}
    game_dir = "game"

    #: @type: L{PluginManager}
    plugins = None

    #: @type: L{mudsling.storage.Database}
    db = None
    db_file_path = ""

    #: @type: L{SessionHandler}
    session_handler = None
    start_time = 0
    restart_time = 0
    exit_code = 0

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

        self.game_dir = gameDir  # Should already be init'd by mudsling.py.

        # Load configuration.
        config.read(configPaths)

    def init_game(self):
        logging.info("Initializing game...")
        self.start_time = time.time()  # Will be re-set by proxy, possibly.
        self.restart_time = self.start_time
        # Setup session handler. Used by services.
        self.session_handler = SessionHandler(self)

        # Load plugin manager. Locates, filters, and loads plugins.
        self.plugins = PluginManager(self, self.game_dir)

        self.init_locks()
        self.load_class_configs()
        registry.classes.build_class_registry(self)
        self.load_database()

        # Dependency injection.
        tasks.BaseTask.game = self
        tasks.BaseTask.db = self.db

        if not self.db.initialized:
            self.init_database()

        # Setup the plugin handling the login screen.
        name = config.get('Main', 'login screen')
        plugin = self.plugins.get_plugins_by_machine_name(name, "LoginScreen")
        if plugin is not None:
            logging.debug("Using %s as LoginScreen" % name)
            self.login_screen = plugin.plugin_object

    # Non-PEP8 naming by Twisted.
    def startService(self):
        self.init_game()
        logging.info("Starting services...")
        # Gather Twisted services and register them to our application.
        for info in self.plugins.active_plugins("TwistedService"):
            service = info.plugin_object.get_service()
            if isinstance(service, Service):
                #service.setServiceParent(self.parent)
                self.addService(service)

        # Setup the AMP server if we are using proxy.
        if config.getboolean('Proxy', 'enabled'):
            service = proxy.AMP_server(self,
                                       config.getint('Proxy', 'AMP port'))
            self.addService(service)

        # Fire server startup hooks.
        self.db.on_server_startup()
        self.invoke_hook('server_startup')

        MultiService.startService(self)

    def load_class_configs(self):
        """
        Cycle through the [Classes] config section, finding the configured
        classes, making sure their modules are loaded and the game has a ref
        to the class object.
        """
        for config_name, class_path in config.items('Classes'):
            attrname = config_name.replace(' ', '_')
            setattr(self, attrname, utils.modules.class_from_path(class_path))

    def init_locks(self):
        """
        Gather the lock functions and initialize the lock parser.
        """
        lockFuncs = lockfuncs.default_funcs()
        hookResponses = self.invoke_hook("lock_functions")
        lockFuncs.update(utils.sequence.dict_merge(*hookResponses.values()))
        logging.info("Loaded %d lock functions", len(lockFuncs))
        # Initialize the parser. The result is cached in the module for future
        # calls to obtain the parser.
        locks.parser(lockFuncs, reset=True)

    def load_database(self):
        dbfilename = config.get('Main', 'db file')
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
        self.db.on_loaded(self)

        # Build the player registry.
        registry.players.register_players(self.db.descendants(BasePlayer))

    # TODO: Refactor this into hooks?
    def init_database(self):
        self.db.initialized = True

        # Create first player.
        #: @type: mudsling.objects.BasePlayer
        player = self.player_class.create(names=['admin'],
                                          email='admin@localhost',
                                          password='pass')
        player.superuser = True

        #: @type: mudsling.objects.BaseCharacter
        char = self.character_class.create(names=['Admin'])
        char.possessable_by = [player]

        player.default_object = char
        player.possess_object(char)

        #: @type: mudsling.topography.Room
        room = self.room_class.create(names=['The First Room'])
        self.db.set_setting('player start', room)
        char.move_to(room)

        task = CheckpointTask()
        task.start(task.configured_interval())

        self.invoke_hook('init_database', self.db)

        # Get the db on disk.
        self.save_database()

    # TODO: Refactor this into the DB layer, so a DB knows how to save itself.
    def save_database(self):
        with open(self.db_file_path, 'wb') as dbfile:
            pickle.dump(self.db, dbfile, -1)

    # noinspection PyShadowingBuiltins
    def shutdown(self, reload=False):
        # Call shutdown hooks.
        self.invoke_hook('server_shutdown', reload=reload)
        self.db.on_server_shutdown()
        self.__exit(10 if reload else 0)

    def reload(self):
        self.shutdown(reload=True)

    def __exit(self, code=0):
        self.exit_code = code
        if code != 10:
            self.session_handler.disconnect_all_sessions("Shutting Down")
        self.save_database()

        def __stop_reactor(result):
            #noinspection PyUnresolvedReferences
            reactor.stop()
        self.stopService().addBoth(__stop_reactor)

    def uptime(self, sinceRestart=False):
        if sinceRestart:
            return time.time() - self.restart_time
        else:
            return time.time() - self.start_time

    def invoke_hook(self, hook, *args, **kwargs):
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
        return self.plugins.invoke_hook('GamePlugin', hook, *args, **kwargs)


class CheckpointTask(tasks.Task):
    def __str__(self):
        return "The Checkpoint Task"

    def run(self):
        self.game.save_database()

    def configured_interval(self):
        return config.getinterval('Main', 'checkpoint interval')

    def on_server_startup(self):
        self.restart(self.configured_interval())
