"""
OOC Commands.
"""

from mudsling.commands import Command
from mudsling import errors
from mudsling import locks

from mudsling import utils
import mudsling.utils.string

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


class HelpCmd(Command):
    """
    help [<topic>]

    Retrieves help on the specified topic. If no topic is given, it will look
    for the "index" help topic.
    """
    aliases = ('help', '@help', '+help')  # All the same help.
    syntax = "[<topic>]"
    lock = locks.AllPass  # Everyone can have help.

    def run(self, this, actor, args):
        search = args['topic'] or 'index'

        def entryFilter(e):
            return e.lock.eval(e, actor)

        try:
            topic = help.help_db.findTopic(search, entryFilter=entryFilter)
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
