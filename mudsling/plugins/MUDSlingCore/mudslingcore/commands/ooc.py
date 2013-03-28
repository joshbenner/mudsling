"""
OOC Commands.
"""

from mudsling.commands import Command
from mudsling.objects import Object
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from mudslingcore.misc import teleport_object
from mudslingcore import help
from mudslingcore.ui import ClassicUI


class AnsiCmd(Command):
    """
    +ansi on|off

    Enable/disable ANSI color.
    """

    aliases = ('+ansi',)
    syntax = "[{ on | off }]"

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """

        if args['optset1'] is None:
            if actor.ansi:
                self.demo()
            else:
                actor.msg('ANSI color is OFF')
            return

        val = args['optset1'] == 'on'

        if actor.ansi == val:
            if val:
                actor.msg("You already have ANSI enabled.")
            else:
                actor.msg("You already have ANSI disabled.")
        else:
            actor.ansi = val

    def demo(self):
        msg = [
            'ANSI color is {gON',
            '  {r{{r Red        {n{R{{R Red',
            '  {g{{g Green      {n{G{{G Green',
            '  {y{{y Yellow     {n{Y{{Y Yellow',
            '  {b{{b Blue       {n{B{{B Blue',
            '  {m{{m Magenta    {n{M{{M Magenta',
            '  {c{{c Cyan       {n{C{{C Cyan',
            '  {w{{w White      {n{W{{W White',
            '  {x{{x Grey       {n{{X (Black)',
            '',
            '  {{n Normal'
        ]
        self.actor.msg('\n'.join(msg))


class GoCmd(Command):
    """
    @go <location>

    Teleport one's self to the indicated location.
    """
    aliases = ('@go',)
    syntax = "<where>"
    required_perm = "teleport self"
    arg_parsers = {
        'where': parsers.MatchObject(cls=Object,
                                     searchFor='location', show=True)
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        if actor.isPosessing and actor.possessing.isValid(Object):
            #: @type: Object
            obj = actor.possessing
            teleport_object(obj, args['where'])
        else:
            raise errors.CommandError("You are not attached to a valid object"
                                      " with location.")


class MoveCmd(Command):
    """
    @move <object> to <location>

    Moves the specified object to the specified location.
    """
    aliases = ('@move', '@tel', '@teleport')
    syntax = "<what> to <where>"
    required_perm = "teleport anything"
    arg_parsers = {
        'what': parsers.MatchObject(cls=Object,
                                    searchFor='locatable object', show=True),
        'where': parsers.MatchObject(cls=Object,
                                     searchFor='location', show=True),
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        teleport_object(args['what'], args['where'])


class HelpCmd(Command):
    """
    help [<topic>]

    Retrieves help on the specified topic. If no topic is given, it will look
    for the "index" help topic.
    """
    aliases = ('help', '@help', '+help')  # All the same help.
    syntax = "[<topic>]"

    def run(self, this, actor, args):
        search = args['topic'] or 'index'
        try:
            topic = help.help_db.findTopic(search)
        except errors.AmbiguousMatch as e:
            msg = "{yNo topic '%s' found." % search
            if e.matches is not None:
                entries = []
                for topic in e.matches:
                    entry = help.help_db.name_map[topic]
                    entries.append(help.mxpLink(entry.title, entry.title))
                lst = utils.string.english_list(entries, andstr=' or ')
                msg += " Were you looking for any of these? {n%s" % lst
            actor.msg(msg)
            return
        except errors.MatchError as e:
            actor.msg('{y' + e.message)
            return

        ui = ClassicUI()
        out = ui.report("Help: %s" % topic.title, topic.mudText())
        actor.msg(out)
