import os
import yapsy.PluginManager

from .plugins import ITwistedServicePlugin, IMUDSlingPluginInfo
from .plugins import IMUDSlingPlugin


class PluginManager(yapsy.PluginManager.PluginManager):

    #: @cvar: Config section identifying enabled plugins.
    PLUGIN_ENABLE_SECTION = "Plugins"

    #: @cvar: Config values for plugins that indicate plugin is enabled.
    PLUGIN_ENABLE_VALUES = ['on', 'enabled', 'enable', 'yes', '1', 'true']

    #: @cvar: Plugin category mappings.
    PLUGIN_CATEGORIES = {
        "TwistedService": ITwistedServicePlugin
    }

    def __init__(self, game_dir, config):
        """
        Initialize plugin manager based on game directory and loaded config.

        @param game_dir: Path to active game directory (which can have plugins)
        @param config: Loaded configuration.
        @type config: ConfigParser.SafeConfigParser
        """
        super(PluginManager, self).__init__(
            plugin_info_ext=IMUDSlingPluginInfo.PLUGIN_INFO_EXTENSION,
            directories_list=self.plugin_paths(game_dir),
            categories_filter=self.PLUGIN_CATEGORIES
        )
        self.setPluginInfoClass(IMUDSlingPluginInfo)

        # Locate all candidate plugins. Parses info files.
        self.locatePlugins()

        # Determine which plugins to load based on configuration.
        enabled_in_config = []
        sec = self.PLUGIN_ENABLE_SECTION
        enabled = self.PLUGIN_ENABLE_VALUES
        if config.has_section(sec):
            for opt_name in config.options(sec):
                if config.get(sec, opt_name).lower() in enabled:
                    enabled_in_config.append(opt_name)

        # Filter candidates to only those enabled in config.
        new_candidates = []
        for infofile, path, info in self._candidates:
            if isinstance(info, IMUDSlingPluginInfo):
                if info.machine_name.lower() in enabled_in_config:
                    new_candidates.append((infofile, path, info))
        self._candidates = new_candidates

        # Load the plugins configured to be enabled.
        self.loadPlugins()

        # Activate all loaded plugins.
        for info in self.getAllPlugins():
            # Load config-based options if Plugin supports them.
            if isinstance(info.plugin_object, IMUDSlingPlugin):
                plugin_section = "Plugin:%s" % info.machine_name
                if config.has_section(plugin_section):
                    info.plugin_object.options = config.items(plugin_section)
            self.activatePluginByName(info.name, info.category)

    def plugin_paths(self, game_dir):
        return ['mudsling/plugins', "%s/plugins" % game_dir]

    def active_plugins(self, category=None):
        if category is None:
            all = self.getAllPlugins()
        else:
            all = self.getPluginsOfCategory(category)

        return [info for info in all if info.is_activated]

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
