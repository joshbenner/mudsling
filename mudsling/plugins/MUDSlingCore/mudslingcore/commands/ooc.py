"""
OOC Commands.
"""

from mudsling.commands import Command


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
            '  {{r {rRed        {n{{R {RRed',
            '  {{g {gGreen      {n{{G {GGreen',
            '  {{y {yYellow     {n{{Y {YYellow',
            '  {{b {bBlue       {n{{B {BBlue',
            '  {{m {mMagenta    {n{{M {MMagenta',
            '  {{c {cCyan       {n{{C {CCyan',
            '  {{w {wWhite      {n{{W {WWhite',
            '  {{x {xGrey       {n{{X {XBlack',
            '',
            ''
        ]
        self.actor.msg('\n'.join(msg))
