import os
import sys
import logging
import inspect
from collections import OrderedDict

from mudsling.config import Config, ConfigSection, config

from mudsling import utils
import mudsling.utils.modules


class PluginError(Exception):
    pass


class PluginInfo(Config):
    path = ''
    filesystem_name = ''
    machine_name = ''
    module = None


class Plugin(object):
    """
    Base plugin class.

    @ivar info: A ConfigParser containing the module information.
    @ivar options: Plugin's config section from the game-specific config.
    @ivar game: Reference to the game object.
    """
    #: :type: PluginInfo
    info = None
    #: :type: mudsling.config.ConfigSection
    options = None
    #: :type: mudsling.core.MUDSling
    game = None
    #: :type: PluginManager
    manager = None

    def __init__(self, game, info, manager):
        """
        Initialize a new instance of a plugin using the info file data.

        :type game: mudsling.core.MUDSling
        :type info: PluginInfo
        :type manager: PluginManager
        """
        self.game = game
        self.info = info
        self.manager = manager
        if config.has_section(info.filesystem_name):
            self.options = config[info.filesystem_name]


class TwistedServicePlugin(Plugin):
    """
    A plugin which provides a twisted service object which will be parented to
    the main application.
    """

    def get_service(self):
        """
        Return a Twisted service object which will be registered to the parent
        application.
        """
        return None


class LoginScreenPlugin(Plugin):
    """
    A plugin that provides the interface upon first connection and the method
    of connecting a 'bare' session with an object.
    """

    def session_connected(self, session):
        """
        Called when a new session is connected.
        :param session: The session that has connected.
        :type session: mudsling.sessions.Session
        """

    def process_input(self, session, input):
        """
        Called when a command is entered by the session.

        :param session: The session which sent the command
        :type session: mudsling.sessions.Session

        :param input: The string sent by the session.
        :type input: str
        """


class GamePlugin(Plugin):
    """
    Game plugins can provide new object classes, hook game events, etc. They're
    the plugins which are meant to interact with the game world in general.
    """

    def server_startup(self):
        """
        This hook is invoked as the last step during server startup, after
        everything is loaded and otherwise ready to go.
        """

    def server_shutdown(self, reload):
        """
        This hook is invoked as the first step in the shutdown process.

        :param reload: If True, the server intends to reload.
        """

    def object_classes(self):
        """
        This hook is called during startup, when MUDSling asks each GamePlugin
        to inform it of object classes the plugin provides which can be
        instantiated via tools like @create.

        :return: (pretty name, class) pairs
        :rtype: list
        """

    def pattern_paths(self):
        """
        Define the paths where MUDSling can find pattern files provided by this
        plugin. Default implementation looks for "patterns" directory within
        the plugin's directory.

        :rtype: list
        """
        path = os.path.join(self.info.path, 'patterns')
        if os.path.exists(path) and os.path.isdir(path):
            return [path]
        return []

    def lock_functions(self):
        """
        This hook is called to get a list of functions that can be used in
        lock strings.

        :return: Map of function name to the function to run.
        :rtype: dict
        """
        return {}

    def init_database(self, db):
        """
        This hook is called when performing initial setup of a database, giving
        GamePlugin instances the opportunity to perform setup of their own.

        :param db: The database being setup.
        """

    def help_paths(self):
        """
        Define the paths where MUDSling can find help files provided by this
        plugin. Default implementation looks for "help" directory within the
        plugin's directory.

        :rtype: list
        """
        path = os.path.join(self.info.path, 'help')
        if os.path.exists(path) and os.path.isdir(path):
            return [path]
        return []


class PluginManager(object):

    #: :cvar: Config section identifying enabled plugins.
    PLUGIN_ENABLE_SECTION = "Plugins"

    #: :cvar: Config values for plugins that indicate plugin is enabled.
    PLUGIN_ENABLE_VALUES = ['on', 'enabled', 'enable', 'yes', '1', 'true']

    #: :cvar: Plugin category mappings.
    PLUGIN_CATEGORIES = {
        "TwistedService": TwistedServicePlugin,
        "LoginScreen": LoginScreenPlugin,
        "GamePlugin": GamePlugin
    }

    INFO_EXT = '.plugin-info'

    #: :type: mudsling.core.MUDSling
    game = None

    def __init__(self, game, paths):
        """
        Initialize plugin manager based on game directory and loaded config.

        Walk plugin paths looking for info files matching enabled plugins.

        :param game: The MUDSling game object.
        :type game: mudsling.core.MUDSling

        :param paths: A list of paths to look for plugins.
        :type paths: list of str
        """
        self.game = game
        plugin_infos = self.find_plugins(paths)
        self.plugins = self.load_plugins(plugin_infos)
        self.check_dependencies()
        self.categories = self.categorize_plugins(self.plugins)

    def enabled_plugins(self):
        enabled_in_config = []
        plugin_section = self.PLUGIN_ENABLE_SECTION
        enable_vals = self.PLUGIN_ENABLE_VALUES
        if config.has_section(plugin_section):
            for opt_name in config.options(plugin_section):
                if config.get(plugin_section, opt_name).lower() in enable_vals:
                    enabled_in_config.append(opt_name)
        return enabled_in_config

    def find_plugins(self, paths):
        enabled_in_config = self.enabled_plugins()
        plugin_infos = {}
        for plugin_dir in paths:
            for dirname, dirnames, files in os.walk(plugin_dir):
                for file in [f for f in files if f.endswith(self.INFO_EXT)]:
                    filesystem_name = file[0:-len(self.INFO_EXT)]
                    machine_name = filesystem_name.lower()
                    if machine_name in enabled_in_config:
                        infopath = os.path.join(dirname, file)
                        info = PluginInfo()
                        info.filesystem_name = filesystem_name
                        info.path = os.path.dirname(infopath)
                        info.machine_name = machine_name
                        try:
                            info.read([infopath])
                        except:
                            logging.fatal("Bad plugin: %s" % machine_name)
                            raise
                        # May replace an already-loaded info by design, so that
                        # more-specific module inclusions can override.
                        plugin_infos[machine_name] = info
        return plugin_infos

    def load_plugins(self, plugin_infos):
        plugins = OrderedDict()
        enabled_in_config = self.enabled_plugins()
        sorter = lambda e: enabled_in_config.index(e)
        for machine_name in sorted(plugin_infos.keys(), key=sorter):
            info = plugin_infos[machine_name]
            # Read default settings.
            defaults = os.path.join(info.path, 'defaults.cfg')
            if os.path.exists(defaults):
                config.read_defaults(defaults)
            if os.path.isfile(os.path.join(info.path, '__init__.py')):
                # Import the entire plugin as a module.
                plugin_mod = utils.modules.mod_import(info.path)
                sys.modules[machine_name] = plugin_mod
            module_filepath = os.path.join(info.path, 'plugin.py')
            if info.has_option('', 'module'):
                config_mod = info.get('', 'module').strip()
                module_filepath = os.path.join(info.path, config_mod)
            module = utils.modules.mod_import(module_filepath)
            info.module = module
            for val in [getattr(module, varname) for varname in dir(module)]:
                if (inspect.isclass(val) and issubclass(val, Plugin)
                        and val.__module__ == module.__name__):
                    plugins[machine_name] = val(self.game, info, self)
                    break
            if machine_name not in plugins:
                raise PluginError("No plugin found in %s" % module_filepath)
        return plugins

    def check_dependencies(self):
        for plugin in self.plugins.itervalues():
            info = plugin.info
            if info.has_option('', 'dependencies'):
                for dep in [d for d in info.getlist('', 'dependencies') if d]:
                    if not dep.lower() in self.plugins:
                        me = info.filesystem_name
                        raise PluginError("%s requires %s" % (me, dep))

    def categorize_plugins(self, plugins):
        categories = {}
        for category in self.PLUGIN_CATEGORIES.keys():
            categories[category] = []
        for plugin in plugins.itervalues():
            for name, cls in self.PLUGIN_CATEGORIES.iteritems():
                if isinstance(plugin, cls):
                    categories[name].append(plugin)
        return categories

    def active_plugins(self, category=None):
        if category is None:
            return self.plugins.values()
        else:
            return self.categories.get(category, [])

    def get_plugin_by_machine_name(self, name, category=None):
        """
        Retrieve an active plugin using its machine name.

        :param name: The machine name of the plugin to retrieve.
        :param category: Limit which plugins are searched by category.

        :rtype: Plugin
        """
        name = name.lower()
        for plugin in self.active_plugins(category):
            if plugin.info.machine_name == name:
                return plugin
        return None

    def invoke_hook(self, category, hook, *args, **kwargs):
        """
        Invoke an arbitrary hook on all activated plugins of a category.

        :param category: The category of plugin to invoke the hook on.
        :param hook: The hook (function) to execute.
        :param args: Positional args to pass to the hook.
        :param kwargs: Keyword args to pass to the hook.
        :return: Dictionary of hook results keyed by plugin info.
        :rtype: dict
        """
        result = {}
        for plugin in self.active_plugins(category):
            try:
                func = getattr(plugin, hook)
            except AttributeError:
                continue
            if callable(func):
                result[plugin.info.machine_name] = func(*args, **kwargs)
        return result

    def __getitem__(self, item):
        return self.get_plugin_by_machine_name(item)

    def __iter__(self):
        for plugin in self.plugins.itervalues():
            yield plugin

    def __contains__(self, item):
        return item in self.plugins
