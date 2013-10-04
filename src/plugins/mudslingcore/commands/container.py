"""
Commands for mudslingcore.objects.Container.
"""
from mudsling import locks, errors
from mudsling.commands import Command
from mudsling.parsers import MatchObject, MatchOtherContents

from mudslingcore.objects import Thing


class PutCmd(Command):
    """
    put <thing> in <container>

    Places a thing inside an open container.
    """
    aliases = ('put', 'place', 'drop')
    syntax = '<thing> {in|into|inside of|inside} <container>'
    arg_parsers = {
        'thing': MatchObject(cls=Thing, search_for='thing', show=True),
        'container': 'this'
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Container
        :type actor: mudslingcore.objects.Object
        :type args: dict
        """
        #: :type: mudslingcore.objects.Object
        thing = args['thing']
        if this.location not in (actor, actor.location):
            actor.tell("You can't get at ", this, ".")
        elif thing.location not in (actor, actor.location):
            actor.tell("You don't have ", thing, ".")
        elif not this.opened:
            actor.tell(this, " is closed.")
        else:
            try:
                thing.move_to(this, by=actor)
            except errors.MoveError as e:
                if e.message:
                    actor.tell('{r', e.message)
                this.emit_message('add_fail', actor=actor, thing=thing)
            else:
                this.emit_message('add', actor=actor, thing=thing)


class TakeCmd(Command):
    """
    take <thing> from <container>

    Remove a thing from an open container.
    """
    aliases = ('take', 'remove', 'get')
    syntax = "<thing> {from|out of|from inside|from inside of} <container>"
    arg_parsers = {
        'thing': None,  # Will be set in execute.
        'container': 'this'
    }
    lock = locks.all_pass

    # Runs before run(), so we can dynamically setup matching.
    def execute(self):
        self.arg_parsers = dict(self.arg_parsers)
        self.arg_parsers['thing'] = MatchOtherContents(self.obj, cls=Thing,
                                                       show=True)
        super(TakeCmd, self).execute()

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Container
        :type actor: mudslingcore.objects.Object
        :type args: dict
        """
        #: :type: mudslingcore.objects.Object
        thing = args['thing']
        if this.location not in (actor, actor.location):
            actor.tell("You are too far away.")
        elif not this.opened:
            actor.tell(this, " is closed.")
        else:
            try:
                try:
                    thing.move_to(actor)
                except errors.MoveDenied as e:
                    if e.denied_by == actor:
                        thing.move_to(actor.location, by=actor)
                        actor.tell('You cannot hold ', thing,
                                   ', and it tumbles to the ground.')
            except errors.MoveError as e:
                if e.message:
                    actor.tell('{r', e.message)
                this.emit_message('remove_fail', actor=actor, thing=thing)
            else:
                this.emit_message('remove', actor=actor, thing=thing)


class OpenCmd(Command):
    """
    open <container>

    Opens a container.
    """
    aliases = ('open',)
    syntax = '<container>'
    arg_parsers = {
        'container': 'this',
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Container
        :type actor: mudslingcore.objects.Object
        :type args: dict
        """
        if not this.can_close:
            actor.tell(this, ' does not open or close.')
        elif this.location not in (actor, actor.location):
            actor.tell('You are too far away.')
        elif this.opened:
            actor.tell(this, ' is already opened.')
        else:
            this.open(opened_by=actor)


class CloseCmd(Command):
    """
    close <container>

    Closes a container.
    """
    aliases = ('close', 'shut')
    syntax = '<container>'
    arg_parsers = {
        'container': 'this',
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.objects.Container
        :type actor: mudslingcore.objects.Object
        :type args: dict
        """
        if not this.can_close:
            actor.tell(this, ' does not open or close.')
        elif this.location not in (actor, actor.location):
            actor.tell('You are too far away.')
        elif not this.opened:
            actor.tell(this, ' is already opened.')
        else:
            this.close(closed_by=actor)
