"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world.
"""

from mudsling.extensibility import GamePlugin
from mudsling.perms import Role

from .mudslingcore.objects import Object
from .mudslingcore.topography import Room


class MUDSlingCorePlugin(GamePlugin):
    """
    Upon activation of this module, its directory will be added to the python
    search path, such that modules and packages within it can be imported, used
    when specifying classes in configs, etc.
    """
    def hook_initDatabase(self, db):
        """
        This hook is called when performing initial setup of a database, giving
        GamePlugin instances the opportunity to perform setup of their own.

        @param db: The database being setup.
        """

    def hook_serverStartup(self):
        """
        This hook is invoked as the last step during server startup, after
        everything is loaded and otherwise ready to go.
        """

    def hook_serverShutdown(self, reload):
        """
        This hook is invoked as the first step in the shutdown process.

        @param reload: If True, the server intends to reload.
        """

    def hook_objectClasses(self):
        """
        This hook is called during startup, when MUDSling asks each GamePlugin
        to inform it of object classes the plugin provides which can be
        instantiated via tools like @create.

        @return: (pretty name, class) pairs
        @rtype: list
        """
        return [
            ('Object', Object),
            ('Room', Room)
        ]
