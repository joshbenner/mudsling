import os

from yapsy.IPlugin import IPlugin
from yapsy.PluginInfo import PluginInfo


class IMUDSlingPluginInfo(PluginInfo):
    """
    Class used with yapsy to describe plugins.
    """

    #: @cvar: The extension used by MUDSling plugin info files.
    PLUGIN_INFO_EXTENSION = "plugin-info"

    #: @ivar: Machine-readable name of the plugin.
    #: @type: str
    machine_name = None

    def __init__(self, plugin_name, plugin_path, filename=""):
        super(IMUDSlingPluginInfo, self).__init__(plugin_name, plugin_path)
        ext_len = len(self.PLUGIN_INFO_EXTENSION) + 1
        self.machine_name = os.path.basename(filename)[:-ext_len]


class IMUDSlingPlugin(IPlugin):
    """
    Base plugin class.
    """

    #: @ivar: Key/val pairs of options loaded from config for this plugin.
    options = {}


class ITwistedServicePlugin(IMUDSlingPlugin):
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
