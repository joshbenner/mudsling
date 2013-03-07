"""
The basic commands to enable a character to do the essentials in a game, such
as movement and looking at things.
"""
from mudsling.commands import Command
from mudslingcore.objects import Thing


class RoomLookCmd(Command):
    aliases = ('look', 'l')
    syntax = "[[at] <something>]"
    valid_args = {
        'something': Thing
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
            if self.game.db.isValid(actor.location, Thing):
                actor.msg(actor.location.seenBy(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: @type: Object
        target = args['something']

        if not target.isValid(Thing):
            actor.msg("You're not sure what you see.")
        else:
            if target in actor._getContext():
                actor.msg(target.seenBy(actor))
            else:
                actor.msg("You don't see any '%s' here."
                          % self.parsed['something'])
