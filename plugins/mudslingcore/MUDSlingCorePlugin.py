"""
The primary plugin module for the MUDSlingCore plugin.

This plugin is an example of the GamePlugin type of plugin, which can expose
new capabilities to the game world.
"""

from mudsling.extensibility import GamePlugin
from mudsling.commands import all_commands
from mudsling.perms import create_default_roles

from mudslingcore.objects import Thing, Character, Player, Container
from mudslingcore.rooms import Room, Exit
from mudslingcore import help
from mudslingcore import mail
from mudslingcore import bans
from mudslingcore import globalvars
import mudslingcore.areas as areas


default_roles = {
    'Core Player': ('use mail',)
}


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
        help.help_db = help.load_help_files(self.game)
        mail.mail_db = mail.MailDB(self.game.game_file_path('mail.sqlite'),
                                   self.game)
        create_default_roles(default_roles)

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
