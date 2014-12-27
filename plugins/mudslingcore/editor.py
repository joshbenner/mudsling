from mudsling.storage import PersistentSlots
from mudsling.objects import BasePlayer
from mudsling.commands import Command
from mudsling import errors


class EditorPlayer(BasePlayer):
    """
    Exposes editor commands for use by player.
    """
    editor_sessions = ()
    active_editor_session = None

    def process_input(self, raw, err=True):
        try:
            return super(EditorPlayer, self).process_input(raw, err=True)
        except errors.CommandInvalid:
            if raw[0] in ('.', "'"):
                self.process_editor_command(raw)
            else:
                raise

    def process_editor_command(self, raw):
        if isinstance(self.active_editor_session, EditorSession):
            self.active_editor_session.process_command(raw)
        raise errors.CommandInvalid(raw)


class EditorSession(PersistentSlots):
    """
    An editor session, storing the current state of the editor.
    """
    __slots__ = ('lines', 'caret')

    commands = ()

    def description(self):
        return 'Some text'

    def process_command(self, raw):
        cmd_matches = []
        for cmdcls in self.commands:
            if cmdcls.


class InlineCommand(Command):
    """
    Specialized command for editors which optionally does not match on only the
    command name, but the entire syntax.
    """
    match_prefix = ''
    abstract = True

    @classmethod
    def matches(cls, cmdstr):
        return cmdstr.startswith(cls.match_prefix)

    def match_syntax(self, argstr):
        full_command = ('%s %s' % (self.cmdstr, argstr)).strip()
        return super(InlineCommand, self).match_syntax(full_command)
