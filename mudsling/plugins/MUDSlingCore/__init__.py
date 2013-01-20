"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world.
"""

from mudsling.extensibility import GamePlugin
from mudsling.perms import Role


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

