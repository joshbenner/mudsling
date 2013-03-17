"""
The basic commands to enable a character to do the essentials in a game, such
as movement and looking at things.
"""
from mudsling.commands import Command
from mudsling import parsers

from mudslingcore.objects import DescribableObject


class RoomLookCmd(Command):
    aliases = ('look', 'l')
    syntax = "[[at] <something>]"
    arg_parsers = {
        'something': parsers.MatchObject(searchFor='thing to look at',
                                         show=True)
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Room
        @type actor: mudslingcore.objects.Character
        @type args: dict
        """
        if args['something'] is None:
            # Naked look.
            #: @type actor.location: Object
            if self.game.db.isValid(actor.location, DescribableObject):
                actor.msg(actor.location.seenBy(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: @type: Object
        target = args['something']

        if target in actor._getContext() or actor.hasPerm('remote look'):
            if target.isValid(DescribableObject):
                actor.msg(target.seenBy(actor))
            else:
                actor.msg(actor.nameFor(target) + "\nYou see nothing of note.")
        else:
            actor.msg("You don't see any '%s' here." % self.args['something'])
