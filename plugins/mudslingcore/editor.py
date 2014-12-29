from mudsling.storage import PersistentSlots
from mudsling.objects import BaseObject
from mudsling.commands import Command
from mudsling import errors
from mudsling import locks

from mudslingcore.commands.admin.objects import match_configurable_obj
from mudslingcore.commands.admin.objects import can_configure


class EditorError(errors.Error):
    pass


class DuplicateSession(EditorError):
    pass


class InvalidSessionKey(EditorError):
    pass


class EditCmd(Command):
    """
    @edit <object>.<setting>

    Open the line editor for a string setting.
    """
    aliases = ('@edit',)
    syntax = '<obj> {.} <setting>'
    arg_parsers = {'obj': match_configurable_obj}
    lock = can_configure

    def run(self, actor, obj, setting):
        """
        :type actor: EditorSessionHost
        :type obj: mudslingcore.objsettings.ConfigurableObject
        :type setting: str
        """
        objsetting = obj.get_obj_setting(setting)
        if objsetting.type != str:
            raise self._err('You can only @edit strings!')
        session = SettingEditorSession(actor, obj, setting)
        try:
            actor.register_editor_session(session, activate=True)
        except EditorError as e:
            raise self._err(e.message)
        actor.tell('You are now editing ', session.description, '.')


class EditorSessionHost(BaseObject):
    """
    Stores editor sessions.
    """
    editor_sessions = []
    active_editor_session = None

    private_commands = (
        EditCmd,
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
            self.editor_sessions = []
        key = session.session_key
        if key in self.keyed_editor_sessions:
            w = session.description
            raise DuplicateSession("Editor session for '%s' already open." % w)
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
        previous = self.active_editor_session
        sessions = self.keyed_editor_sessions
        if key in sessions:
            self.active_editor_session = self.keyed_editor_sessions[key]
        else:
            raise InvalidSessionKey()
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


class SettingEditorSession(EditorSession):
    """
    An editor session that can modify an object setting.
    """
    __slots__ = ('setting_obj', 'setting_name')

    def __init__(self, owner, setting_obj, setting_name):
        """
        :param owner: The owner of the editor session.
        :type owner: EditorSessionHost

        :param setting_obj: The object where the setting is located.
        :type setting_obj: mudslingcore.objsettings.ConfigurableObject

        :param setting_name: The name of the setting to edit.
        :type setting_name: str
        """
        value = setting_obj.get_obj_setting_value(setting_name)
        super(SettingEditorSession, self).__init__(owner, preload=value)
        self.setting_obj = setting_obj
        self.setting_name = setting_name

    @property
    def session_key(self):
        return '%s:#%s.%s' % (self.__class__.__name__, self.setting_obj.obj_id,
                              self.setting_name)

    @property
    def description(self):
        objname = self.owner.name_for(self.setting_obj)
        return "'%s' setting on %s" % (self.setting_name, objname)
