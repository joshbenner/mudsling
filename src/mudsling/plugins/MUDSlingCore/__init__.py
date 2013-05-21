"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world.
"""

from mudsling.extensibility import GamePlugin
from mudsling.perms import Role

from .mudslingcore.objects import Thing, Character, Player, Container
from .mudslingcore.topography import Room, Exit
from .mudslingcore.help import help_db
from .mudslingcore import bans


class MUDSlingCorePlugin(GamePlugin):
    """
    Upon activation of this module, its directory will be added to the python
    search path, such that modules and packages within it can be imported, used
    when specifying classes in configs, etc.
    """

    def server_startup(self):
        # Init the ban system.
        bans.game = self.game
        # Load help files to form an in-memory database of the entries.
        for paths in self.game.invoke_hook('help_paths').itervalues():
            for path in paths:
                help_db.load_help_path(path, rebuild_name_map=False)
        help_db.rebuild_name_map()

    def object_classes(self):
        return [
            ('Thing', Thing),
            ('Container', Container),
            ('Player', Player),
            ('Character', Character),
            ('Room', Room),
            ('Exit', Exit),
        ]

    def lock_functions(self):
        from .mudslingcore.channels import lock_invited, lock_operator
        return {
            'invited': lock_invited,
            'invitees': lock_invited,
            'operator': lock_operator,
            'operators': lock_operator,
        }
