"""
The basic commands to enable a character to do the essentials in a game, such
as inventory management and looking at things.
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
        'something': parsers.MatchObject(search_for='thing to look at',
                                         show=True)
    }
    lock = locks.all_pass  # Everyone can have a look.

    def _is_lookable(self, obj):
        return hasattr(obj, 'seen_by') and callable(obj.seen_by)

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        if args['something'] is None:
            # Naked look.
            if self._is_lookable(actor.location):
                #noinspection PyUnresolvedReferences
                actor.msg(actor.location.seen_by(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: @type: Object
        target = args['something']

        if target in actor._get_context() or actor.has_perm('remote look'):
            if self._is_lookable(target):
                actor.msg(target.seen_by(actor))
            else:
                actor.msg(actor.name_for(target)
                          + "\nYou see nothing of note.")
        else:
            actor.msg("You don't see any '%s' here." % self.args['something'])


class InventoryCmd(Command):
    """
    inventory [<search>]

    Show a list of all the objects you are carrying. If a search is specified,
    then only those items matching the search are shown.
    """
    aliases = ('inventory', 'i')
    syntax = "[<search>]"
    lock = locks.all_pass  # Everyone can see their own inventory.

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        actor.msg("You are carrying:\n" + this.contents_as_seen_by(this))
