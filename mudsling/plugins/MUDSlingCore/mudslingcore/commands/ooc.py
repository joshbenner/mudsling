"""
OOC Commands.
"""

from mudsling.commands import Command


class AnsiCmd(Command):
    """
    +ansi on|off

    Enable/disable ANSI color.
    """

    aliases = (r'\+ansi',)
    args = ('any', 'any', 'any')

    def run(self, this, input, actor):
        """
        @type input: mudsling.parse.ParsedInput
        @type actor: mudslingcore.objects.Player
        """
        on_vals = ['on', 'yes', 'enable', 'enabled', '1', 'true']
        off_vals = ['off', 'no', 'disable', 'disabled', '0', 'false']
        val = True if input.argstr in on_vals else False

        if input.argstr.lower() in on_vals:
            val = True
        elif input.argstr.lower() in off_vals:
            val = False
        else:
            actor.msg(self.syntaxHelp())
            return

        if actor.ansi == val:
            if val:
                actor.msg("You already have ANSI enabled.")
            else:
                actor.msg("You already have ANSI disabled.")
        else:
            actor.ansi = val

