"""
Administrative commands for managing players.
"""
from mudsling import parsers
from mudsling import registry
from mudsling.commands import Command

from mudsling import utils
import mudsling.utils.email


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
        name, aliases = args['names'][0], args['names'][1:]
        email = args['email']
        playerClass = self.game.player_class

        if not playerClass.validPlayerName(name):
            actor.msg("{yPlayer name invalid. Names may contain letters, "
                      "numbers, hyphens, underscores, and apostraphes.")
            return
        if not utils.email.validEmail(email):
            actor.msg("{yEmail invalid.")
            return
        alreadyClaimed = False
        for n in args['names']:
            if registry.players.findByName(n):
                alreadyClaimed = True
                actor.msg("{yThe name '%s' is already taken." % n)
        if alreadyClaimed:
            return

        #: @type: mudsling.objects.BasePlayer
        newPlayer = self.game.db.createObject(cls=playerClass,
                                              name=name, aliases=aliases)
        newPlayer.email = email

        #: @type: mudsling.objects.BaseCharacter
        char = self.game.db.createObject(cls=self.game.character_class,
                                         name=name, aliases=aliases)
        char.possessable_by = [newPlayer]
        newPlayer.default_object = char

        actor.tell("{gPlayer created: {m", newPlayer,
                   "{g With email {y", email, "{g.")
        actor.tell("{gCharacter created: {c", char, "{g.")
