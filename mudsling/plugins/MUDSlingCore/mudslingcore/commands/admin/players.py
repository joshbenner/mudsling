"""
Administrative commands for managing players.
"""
from mudsling import parsers
from mudsling import errors
from mudsling.commands import Command


class MakePlayerCmd(Command):
    """
    @make-player[/send] <name(s)> for <email>

    Creates a new player (and corresponding character) registered with the
    given email. Sends the new player an email if the /send switch is used.
    """
    aliases = ('@make-player', '@new-player', '@create-player')
    syntax = "<names> for <email>"
    lock = 'perm(create players)'
    arg_parsers = {
        'names': parsers.StringListStaticParser,
    }
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
        playerClass = self.game.player_class
        charClass = self.game.character_class

        try:
            newPlayer = playerClass.create(names=args['names'],
                                           email=args['email'])
        except errors.Error as e:
            actor.msg("{y%s" % e)
            return

        try:
            char = charClass.create(names=args['names'])
        except errors.Error as e:
            actor.msg("{y%s" % e)
            newPlayer.delete()
            return

        char.possessable_by = [newPlayer]
        newPlayer.default_object = char

        actor.tell("{gPlayer created: {m", newPlayer,
                   "{g With email {y", newPlayer.email, "{g.")
        actor.tell("{gCharacter created: {c", char, "{g.")
