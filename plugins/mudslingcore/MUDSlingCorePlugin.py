"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world.
"""

from mudsling.extensibility import GamePlugin
from mudsling.commands import all_commands

from mudslingcore.objects import Thing, Character, Player, Container
from mudslingcore.topography import Room, Exit
from mudslingcore.help import help_db
from mudslingcore import bans
from mudslingcore import globalvars
import mudslingcore.areas as areas


class MUDSlingCorePlugin(GamePlugin, areas.AreaProviderPlugin):
    """
    Upon activation of this module, its directory will be added to the python
    search path, such that modules and packages within it can be imported, used
    when specifying classes in configs, etc.
    """

    def __init__(self, game, info, manager):
        super(MUDSlingCorePlugin, self).__init__(game, info, manager)
        # Register the AreaProviderPlugin type so we can query the plugin
        # manager for a list of them later to compile a list of areas.
        manager.PLUGIN_CATEGORIES['AreaProviderPlugin'] \
            = areas.AreaProviderPlugin

    def server_startup(self):
        # Init subsystems.
        bans.game = self.game
        globalvars.db = self.game.db
        # Load help files to form an in-memory database of the entries.
        for paths in self.game.invoke_hook('help_paths').itervalues():
            for path in paths:
                help_db.load_help_path(path, rebuild_name_map=False)
        help_db.rebuild_name_map()

    def plugins_loaded(self):
        if 'restserver' in self.game.plugins.plugins:
            import mudslingcore.commands.apikeys as api_commands
            Player.private_commands.extend(all_commands(api_commands))

    def object_classes(self):
        # List of tuples because we like to keep the order.
        return [
            ('Thing', Thing),
            ('Container', Container),
            ('Player', Player),
            ('Character', Character),
            ('Room', Room),
            ('Exit', Exit),
        ]

    def lock_functions(self):
        from mudslingcore.channels import lock_invited, lock_operator
        from mudslingcore.objsettings import lock_can_configure
        return {
            'invited': lock_invited,
            'invitees': lock_invited,
            'operator': lock_operator,
            'operators': lock_operator,
            'can_configure': lock_can_configure
        }
