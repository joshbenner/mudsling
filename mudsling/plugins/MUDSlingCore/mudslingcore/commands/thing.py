"""
Commands for L{Thing} instances. These objects are the basic "things" which can
be held, handled, etc.
"""
from mudsling import locks, errors
from mudsling.commands import Command


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
    lock = locks.AllPass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Thing}
        @type actor: L{mudslingcore.objects.Object}
        @type args: C{dict}
        """
        if this.location == actor.location:
            try:
                this.moveTo(actor)
            except errors.InvalidObject:
                pass  # take_fail message will run.
            if this.location == actor:
                this.emitMessage('take', location=actor.location, actor=actor)
            else:
                this.emitMessage('take_fail', location=actor.location,
                                 actor=actor)
        elif this.location == actor:
            actor.msg("You already have that!")
        else:
            actor.msg("You don't see that here.")

    @classmethod
    def failedCommandMatchHelp(cls, argstr):
        return "You don't see a '%s' to take." % argstr


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
    lock = locks.AllPass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Thing}
        @type actor: L{mudslingcore.objects.Object}
        @type args: C{dict}
        """
        if this.location == actor:
            try:
                this.moveTo(actor.location)
            except errors.InvalidObject:
                pass
            if this.location == actor:
                this.emitMessage('drop_fail', location=actor.location,
                                 actor=actor)
            else:
                this.emitMessage('drop', location=this.location, actor=actor)
        else:
            actor.msg("You don't have that.")

    @classmethod
    def failedCommandMatchHelp(cls, argstr):
        return "You don't see a '%s' to drop." % argstr
