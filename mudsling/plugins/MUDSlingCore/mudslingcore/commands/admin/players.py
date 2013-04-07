"""
Administrative commands for managing players.
"""
from mudsling import parsers
from mudsling import errors
from mudsling.commands import Command

from mudsling import utils
import mudsling.utils.string


class MakePlayerCmd(Command):
    """
    @make-player <name(s)> [<password>]

    Creates a new player (and corresponding character) registered with the
    given email. Sends the new player an email if the /send switch is used.
    """
    aliases = ('@make-player', '@new-player', '@create-player')
    syntax = "<names> [<password>]"
    lock = 'perm(create players)'
    arg_parsers = {
        'names': parsers.StringListStaticParser,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        playerClass = self.game.player_class
        password = args['password'] or utils.string.randomString(10)

        try:
            newPlayer = playerClass.create(names=args['names'],
                                           password=password,
                                           makeChar=True)
        except errors.Error as e:
            actor.msg("{y%s" % e)
            return

        actor.tell("{gPlayer created: {m", newPlayer,
                   "{g with password '{r", password, "{g'.")
        actor.tell("{gCharacter created: {c", newPlayer.default_object, "{g.")
