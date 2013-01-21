"""
Player commands.
"""
import time
import traceback

from mudsling.commands import Command
from mudsling.ansi import parse_ansi
from mudsling.objects import Object


class EvalCmd(Command):
    """
    @eval <python code>

    Execute arbitrary python code.

    Requires the 'eval code' permission.
    """

    aliases = ('@eval',)
    args = ('any', None, None)
    required_perm = "eval code"

    def run(self, this, input, actor):
        """
        Execute and time the code.

        @type actor: mudslingcore.objects.Player
        """

        code = input.argstr

        #: @type: Object
        char = actor.possessing

        if not code:
            actor.msg(self.syntaxHelp())
            return False

        available_vars = {
            'game': self.game,
            'player': actor,
            'me': char,
            'here': char.location if isinstance(char, Object) else None
        }

        actor.msg("{y>>> %s" % code)

        mode = 'eval'
        duration = None
        #noinspection PyBroadException
        try:
            #noinspection PyBroadException
            try:
                compiled = compile(code, '', 'eval')
            except:
                mode = 'exec'
                compiled = compile(code, '', 'exec')

            begin = time.clock()
            ret = eval(compiled, {}, available_vars)
            duration = time.clock() - begin

            if mode == 'eval':
                ret = "<<< %s" % repr(ret)
            else:
                ret = "<<< Done."
        except:
            error_lines = traceback.format_exc().split('\n')
            if len(error_lines) > 4:
                error_lines = error_lines[4:]
            ret = "\n".join("<<< %s" % line for line in error_lines if line)

        raw_string = parse_ansi("{m") + ret + parse_ansi("{n")
        actor.msg(raw_string, {'raw': True})
        if duration is not None:
            actor.msg("Exec time: %.3f ms" % (duration * 1000))
