"""
Player commands.
"""
import time
import traceback

from mudsling.commands import Command
from mudsling.ansi import parse_ansi


class EvalCmd(Command):
    """
    @eval <python code> -- Executes arbitrary python code.

    Requires the 'eval code' permission.
    """

    aliases = ('@eval',)
    args = ('any', None, None)
    required_perm = "eval code"

    def run(self):
        """
        Execute and time the code.
        """
        code = self.input.argstr

        if not code:
            self.actor.msg(self.syntaxHelp())
            return False

        available_vars = {}

        self.actor.msg("{y>>> %s" % code)

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
        self.actor.msg(raw_string, {'raw': True})
        if duration is not None:
            self.actor.msg("Exec time: %.3f ms" % (duration * 1000))
