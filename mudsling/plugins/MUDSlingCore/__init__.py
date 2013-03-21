"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world. All hooks and plugin API functions expected
by MUDSling will be documented here.
"""

from mudsling.extensibility import GamePlugin
from mudsling.perms import Role

from .mudslingcore.objects import Thing, Character, Player
from .mudslingcore.topography import Room, Exit
from .mudslingcore.help import help_db


class MUDSlingCorePlugin(GamePlugin):
    """
    Upon activation of this module, its directory will be added to the python
    search path, such that modules and packages within it can be imported, used
    when specifying classes in configs, etc.
    """
    def patternPaths(self):
        """
        Called to get a list of pattern file directories. The easiest approach
        is to just let MUDSling find a "patterns" directory in the plugin
        directory. However, if you need to customize paths, this is where you
        have the opportunity.
        """
        return super(MUDSlingCorePlugin, self).patternPaths()

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
        # Load help files to form an in-memory database of the entries.
        for paths in self.game.invokeHook('helpPaths').itervalues():
            for path in paths:
                help_db.loadHelpPath(path, rebuildNameMap=False)
        help_db.rebuildNameMap()

    def hook_helpPaths(self):
        """
        This hook is called to get a list of paths where help files can be
        found. This hook is implemented by mudslingcore, however, and may not
        be called if you are not using mudslingcore.

        The default implementaiton looks for a "help" directory in the plugin's
        path. For most cases, that should be sufficient.
        """
        return super(MUDSlingCorePlugin, self).hook_helpPaths()

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
            ('Thing', Thing),
            ('Player', Player),
            ('Character', Character),
            ('Room', Room),
            ('Exit', Exit),
        ]
