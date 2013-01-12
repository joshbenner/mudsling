import os

from yapsy.IPlugin import IPlugin
from yapsy.PluginInfo import PluginInfo


class IMUDSlingPlugin(IPlugin):
    #: @ivar: Key/val pairs of options loaded from config for this plugin.
    options = {}


class IMUDSlingPluginInfo(PluginInfo):

    #: @cvar: The extension used by MUDSling plugin info files.
    PLUGIN_INFO_EXTENSION = "plugin-info"

    #: @ivar: Machine-readable name of the plugin.
    #: @type: str
    machine_name = None

    def __init__(self, plugin_name, plugin_path, filename=""):
        super(IMUDSlingPluginInfo, self).__init__(plugin_name, plugin_path)
        ext_len = len(self.PLUGIN_INFO_EXTENSION) + 1
        self.machine_name = os.path.basename(filename)[:-ext_len]


class ITwistedServicePlugin(IMUDSlingPlugin):
    def get_service(self):
        """
        Return a Twisted service object which will be registered to the parent
        application.
        """
        return None
