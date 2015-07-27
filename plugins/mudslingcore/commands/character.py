"""
The basic commands to enable a character to do the essentials in a game, such
as inventory management and looking at things.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling import locks
from mudsling import errors
from mudsling.parsers import MatchObject
from mudsling.objects import Object, BaseCharacter

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

        if target in actor.primary_context() or actor.has_perm('remote look'):
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


class TakeThingCmd(Command):
    """
    take <object>

    Picks up an object in the location with you and moves it to your inventory.
    """
    aliases = ('take', 'get', 'pickup')
    key = 'take thing'
    syntax = "<obj>"
    arg_parsers = {
        'obj': MatchObject(cls=Object, search_for='object', show=True),
    }
    lock = locks.all_pass

    def run(self, actor, obj):
        """
        :type actor: mudslingcore.objects.Character
        :type obj: mudsling.object.Object
        """
        from mudslingcore.objects import Thing
        if (actor.has_perm('pick up anything') or obj.isa(Thing)
                or obj.owner == actor):
            if obj.location == actor.location:
                try:
                    obj.move_to(actor, by=actor, via='take')
                except errors.InvalidObject:
                    pass  # take_fail message will run.
                msg = 'take' if obj.location == actor else 'take_fail'
                messager = obj if obj.get_message(msg) is not None else actor
                messager.emit_message(msg, location=actor.location, actor=actor,
                                      obj=obj)
            elif obj.location == actor:
                actor.msg("You already have that!")
            else:
                actor.msg("You don't see that here.")
        else:
            actor.msg("You can't pick that up.")

    def failed_command_match_help(self):
        return "You don't see a '%s' to take." % self.argstr


class DropThingCmd(Command):
    """
    drop <thing>

    Drops an object in your inventory into your location.
    """
    aliases = ('drop',)
    syntax = "<obj>"
    arg_parsers = {
        'obj': MatchObject(cls=Object, search_for='object', show=True),
    }
    lock = locks.all_pass

    def run(self, actor, obj):
        """
        :type actor: mudslingcore.objects.Character
        :type obj: mudsling.objects.Object
        """
        if obj.location == actor:
            try:
                obj.move_to(actor.location)
            except errors.InvalidObject:
                pass
            msg = 'drop_fail' if obj.location == actor else 'drop'
            messager = obj if obj.get_message(msg) is not None else actor
            messager.emit_message(msg, location=actor.location, actor=actor,
                                  obj=obj)
        else:
            actor.msg("You don't have that.")

    def failed_command_match_help(self):
        return "You don't see a '%s' to drop." % self.argstr


class GiveThingCmd(Command):
    """
    give <thing> to <character>

    Gives something you are holding to another character in the same location
    as you.
    """
    aliases = ('give', 'hand')
    syntax = "<obj> to <recipient>"
    arg_parsers = {
        'obj': MatchObject(cls=Object, search_for='object', show=True),
        'char': MatchObject(cls=BaseCharacter, search_for='person', show=True),
    }
    lock = locks.all_pass

    def run(self, actor, obj, recipient):
        """
        :type actor: mudslingcore.objects.Character
        :type obj: mudsling.objects.Object
        :type recipient: mudsling.objects.BaseCharacter
        """
        if obj.location != actor:
            actor.tell("You don't have that!")
        elif recipient.location != actor.location:
            actor.tell("You see no '", self.args['char'], "' here.")
        elif recipient == actor:
            actor.tell("Give it to yourself?")
        else:
            obj.move_to(recipient)
            msg = 'give_fail' if obj.location == actor else 'give'
            messager = obj if obj.get_message(msg) is not None else actor
            messager.emit_message(msg, location=actor.location, actor=actor,
                                  obj=obj, recipient=recipient)
