import os
from collections import OrderedDict

import pkg_resources

from mudsling.config import Config, config


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
    """
    #: :type: pkg_resources.EntryPoint
    entry_point = None
    #: :type: mudsling.config.ConfigSection
    options = None
    #: :type: mudsling.core.MUDSling
    game = None
    #: :type: PluginManager
    manager = None

    def __init__(self, game, entry_point, manager):
        """
        Initialize a new instance of a plugin using the info file data.

        :type game: mudsling.core.MUDSling
        :type entry_point: pkg_resources.EntryPoint
        :type manager: PluginManager
        """
        self.name = entry_point.name.lower()
        self.game = game
        self.entry_point = entry_point
        self.manager = manager
        if self.resource_exists('defaults.cfg'):
            config.read_defaults(self.resource_path('defaults.cfg'))
        if config.has_section(entry_point.name):
            self.options = config[entry_point.name]

    @property
    def module_name(self):
        """:rtype: str"""
        return self.entry_point.module_name

    def resources(self):
        """
        List the plugin's resources.

        :rtype: list[str]
        """
        return pkg_resources.resource_listdir(self.module_name, '')

    def resource_string(self, path):
        """
        Get the contents of a given resource.

        :param path: The resource path to read.
        :type path: str

        :rtype: str
        """
        return pkg_resources.resource_string(self.module_name, path)

    def resource_stream(self, path):
        """
        Get a file-like object for a given resource.

        :param path: The resource path to read.
        :type path: str

        :return: A file-like resource stream.
        """
        return pkg_resources.resource_stream(self.module_name, path)

    def resource_path(self, resource_name):
        """
        Get an extracted filesystem path that can be used to reference a package
        resource.

        :param resource_name: The resource path.
        :type resource_name: str

        :return: The filesystem path to the resource.
        :rtype: str
        """
        return pkg_resources.resource_filename(self.module_name, resource_name)

    def resource_exists(self, resource_name):
        """
        Check if a named resource exists.

        :param resource_name: The name of the resource to check.
        :type resource_name: str

        :rtype: bool
        """
        return pkg_resources.resource_exists(self.module_name, resource_name)


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
        path = self.resource_path('patterns')
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
        path = self.resource_path('help')
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

    def __init__(self, game):
        """
        Initialize plugin manager based on game directory and loaded config.

        Plugins are discovered based on entry_points definitions of other
        distributions installed at the site.

        :param game: The MUDSling game object.
        :type game: mudsling.core.MUDSling
        """
        self.game = game
        enabled_plugins = self.enabled_plugins()
        to_load = filter(lambda p: p.name.lower() in enabled_plugins,
                         self.available_plugins())
        to_load = sorted(to_load,
                         key=lambda p: enabled_plugins.index(p.name.lower()))
        self.plugins = self.activate_plugins(to_load)
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

    @staticmethod
    def available_plugins():
        return list(pkg_resources.iter_entry_points(group='mudsling.plugin',
                                                    name=None))

    def activate_plugins(self, plugin_entry_points):
        """
        Activate a list of given MUDSling Plugin Entry Points.

        :param plugin_entry_points: The plugin entry point to activate.
        :type plugin_entry_points: list[pkg_resources.EntryPoint]

        :return: The activated plugin objects.
        :rtype: dict[str, Plugin]
        """
        activated = OrderedDict()
        for plugin_ep in plugin_entry_points:
            plugin_name = plugin_ep.name.lower()
            plugin_class = plugin_ep.load()
            activated[plugin_name] = plugin_class(self.game, plugin_ep, self)
        return activated

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
            if plugin.name == name:
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
                result[plugin.name] = func(*args, **kwargs)
        return result

    def __getitem__(self, item):
        return self.get_plugin_by_machine_name(item)

    def __iter__(self):
        for plugin in self.plugins.itervalues():
            yield plugin

    def __contains__(self, item):
        return item in self.plugins
