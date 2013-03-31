"""
The basic commands to enable a character to do the essentials in a game, such
as movement and looking at things.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling import locks


class LookCmd(Command):
    """
    look [[at] <something>]

    Look at the room or specified object, seeing the description thereof.
    """
    aliases = ('look', 'l')
    syntax = "[[at] <something>]"
    arg_parsers = {
        'something': parsers.MatchObject(searchFor='thing to look at',
                                         show=True)
    }
    lock = locks.AllPass  # Everyone can have a look.

    def _isLookable(self, obj):
        return hasattr(obj, 'seenBy') and callable(obj.seenBy)

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Character
        @type actor: mudslingcore.objects.Character
        @type args: dict
        """
        if args['something'] is None:
            # Naked look.
            #: @type actor.location: Object
            if self._isLookable(actor.location):
                actor.msg(actor.location.seenBy(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: @type: Object
        target = args['something']

        if target in actor._getContext() or actor.hasPerm('remote look'):
            if self._isLookable(target):
                actor.msg(target.seenBy(actor))
            else:
                actor.msg(actor.nameFor(target) + "\nYou see nothing of note.")
        else:
            actor.msg("You don't see any '%s' here." % self.args['something'])
