from mudsling.storage import PersistentSlots
from mudsling.objects import BaseObject
from mudsling.commands import Command
from mudsling import errors
from mudsling import locks
from mudsling import parsers


class EditorError(errors.Error):
    pass


class DuplicateSession(EditorError):
    pass


class InvalidSessionKey(EditorError):
    pass


class EditorsCmd(Command):
    """
    @editors

    List all the open editor sessions for a session host.
    """
    aliases = ('@editors',)
    lock = locks.all_pass

    def run(self, this, actor):
        """
        :type this: EditorSessionHost
        :type actor: EditorSessionHost
        """
        show = ['{cCurrent editor sessions:']
        c = 0
        active = this.active_editor_session
        for session in this.editor_sessions:
            c += 1
            a = '{g(active){n' if (session == active) else '        '
            show.append('%s %d. %s' % (a, c, session.description))
        actor.msg('\n'.join(show))


class SwitchEditorCmd(Command):
    """
    @switch-editor <session-num>|off

    Switch to another editor session, or deactivate all editors.
    """
    aliases = ('@switch-editor',)
    syntax = ("off", "<num>")
    arg_parsers = {'num': parsers.IntStaticParser}
    lock = locks.all_pass

    def run(self, this, actor, num=None):
        """
        :type this: EditorSessionHost
        :type actor: EditorSessionHost
        :type num: int or None
        """
        if isinstance(num, int):
            sessions = this.editor_sessions
            if 0 < num <= len(sessions):
                session = sessions[num - 1]
                if session == this.active_editor_session:
                    actor.tell('{yYou are already editing ',
                               session.description, '.')
                else:
                    prev = this.activate_editor_session(session.session_key)
                    if prev is not None:
                        actor.tell('No longer editing ', prev.description, '.')
                    actor.tell('{gYou are now editing ', session.description,
                               '.')
            else:
                raise self._err('Invalid editor session number.')
        elif self.argstr == 'off':
            session = this.deactivate_editor_session()
            if session is not None:
                d = session.description
                actor.tell("Editor session deactivated. Was editing ", d, '.')
            else:
                actor.tell('{yNo editor session is active.')


class EditorSessionHost(BaseObject):
    """
    Stores editor sessions.
    """
    #: :type: list of EditorSession
    editor_sessions = []
    active_editor_session = None

    private_commands = (
        EditorsCmd,
        SwitchEditorCmd
    )

    def process_input(self, raw, err=True):
        handled = super(EditorSessionHost, self).process_input(raw, err=False)
        if not handled and raw[0] in ('.', "'"):
            try:
                return self.process_editor_command(raw)
            except errors.CommandError:
                if err:
                    raise
        return handled

    def process_editor_command(self, raw):
        if isinstance(self.active_editor_session, EditorSession):
            return self.active_editor_session.process_command(raw,
                                                              game=self.game)
        raise errors.CommandInvalid(raw)

    @property
    def keyed_editor_sessions(self):
        """
        Gets a dictionary of session keys that map to sessions.
        :return: dict
        """
        return {s.session_key: s for s in self.editor_sessions}

    def register_editor_session(self, session, activate=True):
        """
        Attach a new editor session to the session host.

        :param session: The session to attach.
        :type session: EditorSession
        """
        if 'editor_sessions' not in self.__dict__:
            #: :type: list of EditorSession
            self.editor_sessions = []
        key = session.session_key
        if key in self.keyed_editor_sessions:
            w = session.description
            raise DuplicateSession("Editor session for %s already open." % w)
        self.editor_sessions.append(session)
        if activate:
            self.activate_editor_session(key)

    def activate_editor_session(self, key):
        """
        Activate a session by its session key.

        :param key: The key of the session to activate.
        :type key: str

        :return: The session that was previously active.
        :rtype: EditorSession
        """
        sessions = self.keyed_editor_sessions
        if key in sessions:
            previous = self.deactivate_editor_session()
            #: :type: EditorSession
            self.active_editor_session = sessions[key]
            return previous
        else:
            raise InvalidSessionKey()

    def deactivate_editor_session(self):
        """
        Deactivates the currently-active session.

        :returns: The previously-active session, if any.
        :rtype: EditorSession or None
        """
        previous = self.active_editor_session
        self.active_editor_session = None
        return previous


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





class EditorSession(PersistentSlots):
    """
    An editor session, storing the current state of the editor.
    """
    __slots__ = ('lines', 'caret', 'owner')

    commands = ()

    def __init__(self, owner, preload=''):
        self.owner = owner.ref()
        self.lines = preload.splitlines() if isinstance(preload, str) else []
        self.caret = len(self.lines)

    @property
    def session_key(self):
        """
        Return a machine-comparable key describing what is being edited. This
        is used to detect duplicate editor sessions.
        """
        raise NotImplementedError()

    @property
    def description(self):
        """
        Return a human-readable description of what is being edited.
        """
        raise NotImplementedError()

    def process_command(self, raw, game):
        cmdstr, _, argstr = raw.partition(' ')
        cmd_matches = [c(raw, cmdstr, argstr, game, None, self.owner)
                       for c in self.commands if c.matches(raw)]
        syntax_matches = [c for c in cmd_matches if c.match_syntax(argstr)]
        if len(syntax_matches) > 1:
            raise errors.AmbiguousMatch(msg="Ambiguous Command", query=raw,
                                        matches=syntax_matches)
        if len(syntax_matches) < 1:
            if len(cmd_matches):
                msg = [c.failed_command_match_help() for c in cmd_matches]
                if msg:
                    raise errors.CommandError(msg='\n'.join(msg))
            return False
        syntax_matches[0].execute()
        return True
