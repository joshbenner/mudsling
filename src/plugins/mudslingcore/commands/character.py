"""
The basic commands to enable a character to do the essentials in a game, such
as inventory management and looking at things.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling import locks

from mudsling import utils
import mudsling.utils.string

from mudslingcore.genders import genders


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
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        if not this.can_see:
            actor.msg("{yYou are unable to see.")
            return
        if 'something' not in args or args['something'] is None:
            # Naked look.
            if self._is_lookable(actor.location):
                #noinspection PyUnresolvedReferences
                actor.msg(actor.location.seen_by(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: :type: Object
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
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        actor.msg("You are carrying:\n" + this.contents_as_seen_by(this))


class SayCmd(Command):
    """
    say <speech>

    Emits speech into the character's location.
    """
    aliases = ('say',)
    syntax = '<speech>'
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        this.say(args['speech'])


class EmoteCmd(Command):
    """
    emote [:]<pose>

    Emits to the character's location that the character is doing something.
    """
    aliases = ('emote', 'pose')
    syntax = '[:]<pose>'
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        this.emote(args['pose'],
                   sep='' if self.argstr.startswith(':') else ' ')


class EmitCmd(Command):
    """
    emit <text>

    Emits to the character's location a completely freeform message.
    """
    aliases = ('emit', 'spoof')
    syntax = '<text>'
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        this.emote(args['text'], show_name=False, sep='')



class GenderCmd(Command):
    """
    @gender [<gender>]
    """
    aliases = ('@gender',)
    syntax = '[<gender>]'
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        if args['gender'] is not None:
            gender_name = args['gender'].lower()
            if gender_name in genders:
                this.gender = genders[gender_name]
                actor.tell('You are now a {c', this.gender.name, '{n.')
            else:
                actor.tell('{yUnknown gender: {c', gender_name)
        else:
            actor.tell('You are a {c', actor.gender.name, '{n.')
            all = sorted(["{c%s{n" % g.name for g in genders.itervalues()])
            actor.tell('Valid genders: ', utils.string.english_list(all))
