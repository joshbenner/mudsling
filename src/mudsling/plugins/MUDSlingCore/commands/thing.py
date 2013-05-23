"""
Commands for L{Thing} instances. These objects are the basic "things" which can
be held, handled, etc.
"""
from mudsling import locks, errors
from mudsling.commands import Command
from mudsling.parsers import MatchObject

from mudslingcore.objects import Character


class TakeThingCmd(Command):
    """
    take <thing>

    Picks up an object in the location with you and moves it to your inventory.
    """
    aliases = ('take', 'get', 'pickup')
    syntax = "<obj>"
    arg_parsers = {
        'obj': 'this',
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Thing}
        @type actor: L{mudslingcore.objects.Object}
        @type args: C{dict}
        """
        if this.location == actor.location:
            try:
                this.move_to(actor)
            except errors.InvalidObject:
                pass  # take_fail message will run.
            if this.location == actor:
                this.emit_message('take', location=actor.location, actor=actor)
            else:
                this.emit_message('take_fail', location=actor.location,
                                  actor=actor)
        elif this.location == actor:
            actor.msg("You already have that!")
        else:
            actor.msg("You don't see that here.")

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
        'obj': 'this',
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Thing}
        @type actor: L{mudslingcore.objects.Object}
        @type args: C{dict}
        """
        if this.location == actor:
            try:
                this.move_to(actor.location)
            except errors.InvalidObject:
                pass
            if this.location == actor:
                this.emit_message('drop_fail', location=actor.location,
                                  actor=actor)
            else:
                this.emit_message('drop', location=this.location, actor=actor)
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
    syntax = "<thing> to <char>"
    arg_parsers = {
        'thing': 'this',
        'char': MatchObject(cls=Character, search_for='person', show=True),
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Thing}
        @type actor: L{mudslingcore.objects.Object}
        @type args: C{dict}
        """
        recipient = args['char']

        if this.location != actor:
            actor.tell("You don't have that!")
        elif recipient.location != actor.location:
            actor.tell("You see no '", self.args['char'], "' here.")
        elif recipient == actor:
            actor.tell("Give it to yourself?")
        else:
            this.move_to(recipient)
            this.emit_message('give', actor=actor, recipient=recipient,
                              location=actor.location)
