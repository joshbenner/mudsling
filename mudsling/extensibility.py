import os
import sys

from yapsy.IPlugin import IPlugin
from yapsy.PluginInfo import PluginInfo
import yapsy.PluginManager


class MUDSlingPluginInfo(PluginInfo):
    """
    Class used with yapsy to describe plugins.
    """

    #: @cvar: The extension used by MUDSling plugin info files.
    PLUGIN_INFO_EXTENSION = "plugin-info"

    #: @ivar: Machine-readable name of the plugin.
    #: @type: str
    machine_name = None

    def __init__(self, plugin_name, plugin_path, filename=""):
        super(MUDSlingPluginInfo, self).__init__(plugin_name, plugin_path)
        ext_len = len(self.PLUGIN_INFO_EXTENSION) + 1
        self.machine_name = os.path.basename(filename)[:-ext_len]


class MUDSlingPlugin(IPlugin):
    """
    Base plugin class.

    @ivar options: Key/val pairs of options loaded from config for this plugin.
    @ivar game: Reference to the game object.
    @ivar info: Reference back to the plugin info object.
    """

    options = {}
    info = None
    #: @type: mudsling.server.MUDSling
    game = None


class TwistedServicePlugin(MUDSlingPlugin):
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


class LoginScreenPlugin(MUDSlingPlugin):
    """
    A plugin that provides the interface upon first connection and the method
    of connecting a 'bare' session with an object.
    """

    def sessionConnected(self, session):
        """
        Called when a new session is connected.
        @param session: The session that has connected.
        @type session: mudsling.sessions.Session
        """

    def processInput(self, session, input):
        """
        Called when a command is entered by the session.

        @param session: The session which sent the command
        @type session: mudsling.sessions.Session

        @param input: The string sent by the session.
        @type input: str
        """


class GamePlugin(MUDSlingPlugin):
    """
    Game plugins can provide new object classes, hook game events, etc. They're
    the plugins which are meant to interact with the game world in general.
    """

    def activate(self):
        super(GamePlugin, self).activate()

        # Add plugin's path to the PYTHONPATH so that it may be used as a
        # module by other code, have its classes used in config, etc.
        pluginpath = os.path.dirname(self.info.path)
        sys.path.append(pluginpath)


class PluginManager(yapsy.PluginManager.PluginManager):

    #: @cvar: Config section identifying enabled plugins.
    PLUGIN_ENABLE_SECTION = "Plugins"

    #: @cvar: Config values for plugins that indicate plugin is enabled.
    PLUGIN_ENABLE_VALUES = ['on', 'enabled', 'enable', 'yes', '1', 'true']

    #: @cvar: Plugin category mappings.
    PLUGIN_CATEGORIES = {
        "TwistedService": TwistedServicePlugin,
        "LoginScreen": LoginScreenPlugin,
        "GamePlugin": GamePlugin
    }

    def __init__(self, game, game_dir):
        """
        Initialize plugin manager based on game directory and loaded config.

        @param game: The MUDSling game object.
        @type game: mudsling.server.MUDSling

        @param game_dir: Path to active game directory (which can have plugins)
        """
        super(PluginManager, self).__init__(
            plugin_info_ext=MUDSlingPluginInfo.PLUGIN_INFO_EXTENSION,
            directories_list=self.pluginPaths(game_dir),
            categories_filter=self.PLUGIN_CATEGORIES
        )
        self.setPluginInfoClass(MUDSlingPluginInfo)

        # Locate all candidate plugins. Parses info files.
        self.locatePlugins()

        # Determine which plugins to load based on configuration.
        enabled_in_config = []
        sec = self.PLUGIN_ENABLE_SECTION
        enabled = self.PLUGIN_ENABLE_VALUES
        if game.config.has_section(sec):
            for opt_name in game.config.options(sec):
                if game.config.get(sec, opt_name).lower() in enabled:
                    enabled_in_config.append(opt_name)

        # Filter candidates to only those enabled in config.
        new_candidates = []
        for infofile, path, info in self._candidates:
            if isinstance(info, MUDSlingPluginInfo):
                if info.machine_name.lower() in enabled_in_config:
                    new_candidates.append((infofile, path, info))
        self._candidates = new_candidates

        # Load the plugins configured to be enabled.
        self.loadPlugins()

        # Activate all loaded plugins.
        for info in self.getAllPlugins():
            # Load config-based options if Plugin supports them.
            if isinstance(info.plugin_object, MUDSlingPlugin):
                info.plugin_object.game = game
                info.plugin_object.info = info
                sec = "Plugin:%s" % info.machine_name
                if game.config.has_section(sec):
                    info.plugin_object.options = dict(game.config.items(sec))
            self.activatePluginByName(info.name, info.category)

    def pluginPaths(self, game_dir):
        return ['mudsling/plugins', "%s/plugins" % game_dir]

    def activePlugins(self, category=None):
        if category is None:
            all = self.getAllPlugins()
        else:
            all = self.getPluginsOfCategory(category)

        return [info for info in all if info.is_activated]

    def getPluginByMachineName(self, name, category=None):
        """
        Retrieve an active plugin using its machine name.

        @param name: The machine name of the plugin to retrieve.
        @param category: Limit which plugins are searched by category.

        @return: MUDSlingPlugin
        """
        for info in self.activePlugins(category):
            if info.machine_name == name:
                return info
        return None

    def invokeHook(self, category, hook, *args, **kwargs):
        """
        Invoke an arbitrary hook on all activated plugins of a category.

        @param category: The category of plugin to invoke the hook on.
        @param hook: The hook (function) to execute.
        @param args: Positional args to pass to the hook.
        @param kwargs: Keyword args to pass to the hook.
        @return: Dictionary of hook results keyed by plugin info.
        @rtype: dict
        """
        result = {}
        for info in self.activePlugins(category):
            plugin = info.plugin_object
            try:
                func = getattr(plugin, hook)
            except AttributeError:
                continue
            if callable(func):
                result[info] = func(*args, **kwargs)
        return result

    # Override normal behavior so that we can generate machine name.
    def _gatherCorePluginInfo(self, directory, filename):
        """
        Gather the core information (name, and module to be loaded)
        about a plugin described by it's info file (found at
        'directory/filename').

        Return an instance of ``self.plugin_info_cls`` and the
        config_parser used to gather the core data *in a tuple*, if the
        required info could be localised, else return ``(None,None)``.

        .. note:: This is supposed to be used internally by subclasses
            and decorators.

        """
        # now we can consider the file as a serious candidate
        candidate_infofile = os.path.join(directory, filename)
        # parse the information file to get info about the plugin
        name, moduleName, config_parser =\
            self._getPluginNameAndModuleFromStream(open(candidate_infofile),
                                                   candidate_infofile)
        if (name, moduleName, config_parser) == (None, None, None):
            return None, None
            # start collecting essential info
        info = self._plugin_info_cls(name,
                                     os.path.join(directory, moduleName),
                                     filename)
        return info, config_parser
