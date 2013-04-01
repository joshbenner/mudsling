"""
Administrative commands for managing players.
"""
from mudsling import parsers
from mudsling.commands import Command


class MakePlayerCmd(Command):
    """
    @make-player[/send] <name> for <email>

    Creates a new player (and corresponding character) registered with the
    given email. Sends the new player an email if the /send switch is used.
    """
    aliases = ('@make-player', '@new-player', '@create-player')
    syntax = "<name> for <email>"
    lock = 'perm(create players)'
    switch_parsers = {
        'send': parsers.BoolStaticParser,
    }
    switch_defaults = {
        'send': False,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """

