import time
import traceback
import mudsling

from mudsling.commands import Command
from mudsling.objects import Object
from mudsling.utils import string
from mudsling.storage import ObjRef


class ShutdownCmd(Command):
    """
    @shutdown

    Shutdown the server (and proxy).
    """
    aliases = ('@shutdown',)
    lock = "perm(shutdown server)"

    def run(self, this, actor, args):
        msg = "Shutting down server. Goodbye."
        self.game.session_handler.output_to_all_sessions(msg)
        self.game.shutdown()


class ReloadCmd(Command):
    """
    @reload

    Reloads the server. Only works in proxy mode.
    """
    aliases = ('@reload',)
    lock = "perm(reload server)"

    def _do_reload(self, result):
        self.game.shutdown(reload=True)

    def run(self, this, actor, args):
        msg = "Reloading server, please stand by..."
        d = self.game.session_handler.output_to_all_sessions(msg)
        d.addCallback(self._do_reload)


class EvalCmd(Command):
    """
    @eval <python code>

    Execute arbitrary python code.
    """

    aliases = ('@eval',)
    syntax = "<code>"
    lock = "perm(eval code)"

    def run(self, this, actor, args):
        """
        Execute and time the code.

        @type actor: mudslingcore.objects.Player
        """
        import sys
        import datetime
        import calendar
        from mudsling import registry
        from mudsling.config import config

        # args['code'] isn't reliable since the semicolon shortcut may skip
        # parsing the args via syntax.
        code = self.argstr

        #: @type: Object
        char = actor.possessing

        if not code:
            actor.msg(self.syntax_help())
            return False

        available_vars = {
            'eval_cmd': self,
            'sys': sys,
            'time': time,
            'datetime': datetime,
            'calendar': calendar,
            'game': self.game,
            'ref': self.game.db.get_ref,
            'registry': registry,
            'config': config,
            'player': actor,
            'me': char,
            'here': (char.location if self.game.db.is_valid(char, Object)
                     else None),
            'mudsling': mudsling,
            'utils': mudsling.utils,
        }
        for plugin in self.game.plugins:
            if plugin.info.module is not None:
                mn = plugin.info.machine_name
                if mn in sys.modules:
                    available_vars[mn] = sys.modules[mn]

        inMsg = string.parse_ansi('{y>>> ') + code + string.parse_ansi("{n")
        actor.msg(inMsg, {'raw': True})

        mode = 'eval'
        duration = compile_time = None
        #noinspection PyBroadException
        try:
            begin = time.clock()
            #noinspection PyBroadException
            try:
                compiled = compile(code, '', 'eval')
            except:
                mode = 'exec'
                compiled = compile(code, '', 'exec')
            compile_time = time.clock() - begin

            begin = time.clock()
            ret = eval(compiled, {}, available_vars)
            duration = time.clock() - begin

            if mode == 'eval':
                out = "<<< %s" % repr(ret)
                if isinstance(ret, ObjRef):
                    if ret.is_valid():
                        name = "%s (%s)" % (ret.class_name(),
                                            ret.python_class_name())
                    else:
                        name = 'INVALID'
                    out += " [%s]" % name
            else:
                out = "<<< Done."
        except SystemExit:
            raise
        except:
            error_lines = traceback.format_exc().split('\n')
            if len(error_lines) > 4:
                error_lines = error_lines[4:]
            out = "\n".join("<<< %s" % line for line in error_lines if line)

        raw_string = string.parse_ansi("{m") + out + string.parse_ansi("{n")
        actor.msg(raw_string, {'raw': True})
        if duration is not None:
            msg = "Exec time: %.3f ms, Compile time: %.3f ms (total: %.3f ms)"
            actor.msg(msg % (duration * 1000,
                             compile_time * 1000,
                             (duration + compile_time) * 1000))