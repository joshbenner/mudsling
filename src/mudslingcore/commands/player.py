"""
OOC Commands.
"""

from mudsling.commands import Command
from mudsling import errors
from mudsling import locks
from mudsling.parsers import MatchDescendants
from mudsling.objects import BasePlayer

from mudsling import utils
import mudsling.utils.string

from mudslingcore import help
from mudslingcore.ui import ClassicUI


class AnsiCmd(Command):
    """
    @ansi on|off|256

    Enable/disable ANSI color.
    """

    aliases = ('@ansi',)
    syntax = "[{ on | off | 256}]"
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """

        if 'optset1' not in args:
            if actor.ansi:
                self.demo()
                actor.tell('\n256 color support is: ',
                           '{gON' if actor.xterm256 else '{rOFF')
                actor.msg(self.syntax_help())
            else:
                actor.msg('ANSI color is OFF')
            return

        val = args['optset1'] in ('on', '256')

        if actor.ansi == val:
            if val:
                actor.msg("You already have ANSI enabled.")
            else:
                actor.msg("You already have ANSI disabled.")
        else:
            actor.ansi = val

        xterm256 = args['optset1'] == '256'

        if actor.xterm256 == xterm256:
            if xterm256:
                actor.msg('You already have 256 color support enabled.')
            else:
                actor.msg('You already have 256 color support disabled.')
        else:
            actor.xterm256 = xterm256

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
    aliases = ('help', '@help')  # All the same help.
    syntax = "[<topic>]"
    lock = locks.all_pass  # Everyone can have help.

    def run(self, this, actor, args):
        search = args['topic'] or 'index'

        def entryFilter(e):
            return e.lock.eval(e, actor)

        try:
            topic = actor.find_help_topic(search)
        except errors.AmbiguousMatch as e:
            msg = "{yNo topic '%s' found." % search
            if e.matches is not None:
                entries = []
                for topic in e.matches:
                    entry = help.help_db.name_map[topic]
                    entries.append(help.mxp_link(entry.title, entry.title))
                lst = utils.string.english_list(entries, andstr=' or ')
                msg += " Were you looking for any of these? {n%s" % lst
            actor.msg(msg)
            return
        except errors.MatchError as e:
            actor.msg('{y' + e.message)
            return

        ui = ClassicUI()
        out = ui.report("Help: %s" % topic.title, topic.mud_text())
        actor.msg(out)


class WhoCmd(Command):
    """
    @who

    Displays a list of connected players.
    """
    aliases = ('@who', 'who')
    lock = locks.all_pass

    def format_attached(self, player):
        if player.is_possessing:
            return self.actor.name_for(player.possessing)
        else:
            return ''

    def format_location(self, player):
        try:
            return self.actor.name_for(player.possessing.location)
        except AttributeError:
            return ''

    def run(self, this, actor, args):
        title = 'Who is Online'
        admin = actor.has_perm('manage players')
        ui = ClassicUI(width=100 if admin else 60)
        cols = [
            ui.Column('Player name', data_key='player', align='l', width='*',
                      cell_formatter=actor.name_for),
            ui.Column('Connected', data_key='connected_seconds', align='r',
                      cell_formatter=ui.format_dhms),
            ui.Column('Idle time', data_key='idle_seconds', align='r',
                      cell_formatter=ui.format_dhms),
        ]
        if admin:
            title += ' (admin view)'
            cols.extend([
                ui.Column('Attached to', data_key='player', align='l',
                          cell_formatter=self.format_attached),
                ui.Column('Location', data_key='player', align='l',
                          cell_formatter=self.format_location),
            ])
        table = ui.Table(cols)
        sessions = [s for s in self.game.session_handler.sessions
                    if s.player is not None]
        sessions.sort(key=lambda s: s.idle_seconds())
        table.add_rows(*sessions)
        actor.msg(ui.report(title, table))


class PageCmd(Command):
    """
    page <player>=<message>
    """
    aliases = ('page', '@page', 'p', '@p')
    # Using {=} instead of just = allows the equals to work with no spaces.
    syntax = '<player> {=} <message>'
    arg_parsers = {
        'player': MatchDescendants(cls=BasePlayer, search_for='player',
                                   show=True)
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        msg = args['message']
        recipient = args['player']
        if msg.startswith(':'):
            msg = msg[1:]
            if msg.startswith(':'):
                msg = msg[1:]
                send = [actor, msg]
            else:
                send = [actor, ' ', msg]
            echo = ['{YTo ', recipient, ': ']
            echo.extend(send)
            send.insert(0, '{yFrom afar, ')
        else:
            send = ['{y', actor, ' pages, "', msg, '".']
            echo = ['{YYou page ', recipient, ' with, "', msg, '".']
        actor.tell(*echo)
        recipient.tell(*send)
