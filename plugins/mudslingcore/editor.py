import re
import abc

from mudsling.storage import PersistentSlots
from mudsling.objects import BaseObject
from mudsling.commands import Command
from mudsling import errors
from mudsling import locks
from mudsling import parsers
from mudsling.utils import object as obj_utils


class EditorError(errors.Error):
    pass


class DuplicateSession(EditorError):
    pass


class InvalidSessionKey(EditorError):
    pass


class InvalidRangeSyntax(errors.ParseError):
    pass


class InvalidLineSyntax(errors.ParseError):
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

    def terminate_editor_session(self, key):
        """
        Remove the session from the list of sessions and return it.

        Deactivates session if it is currently active.

        :returns: The session
        :rtype: EditorSession
        """
        sessions = self.keyed_editor_sessions
        if key in sessions:
            session = sessions[key]
            if self.active_editor_session == session:
                self.deactivate_editor_session()
            self.editor_sessions.remove(session)
            return session
        else:
            raise InvalidSessionKey()


class EditorSessionCommand(Command):
    """
    Specialized command for editors which optionally does not match on only the
    command name, but the entire syntax.
    """
    __metaclass__ = abc.ABCMeta
    match_prefix = ''
    lock = locks.all_pass

    @property
    def session(self):
        """
        :rtype: EditorSession
        """
        return self.obj

    @classmethod
    def matches(cls, cmdstr):
        return cmdstr.startswith(cls.match_prefix)

    @classmethod
    def exactly_matches(cls, cmdstr):
        return cls.match_prefix == cmdstr

    def match_syntax(self, argstr):
        if self.syntax == '':
            return True
        self._insert_session_parsers()
        return super(EditorSessionCommand, self).match_syntax(self.raw)

    def _insert_session_parsers(self):
        session_parsers = self.session.parsers
        for argname, parser in self.arg_parsers.iteritems():
            if parser in session_parsers:
                self.arg_parsers[argname] = session_parsers[parser]


class InsertTextCmd(EditorSessionCommand):
    """
    '<text>

    Insert text at current position.
    """
    key = 'addline'
    match_prefix = "'"
    syntax = "'[<text>]"

    def run(self, this, actor, text):
        """
        :type this: EditorSession
        :type actor: BaseObject
        """
        if text is None:
            text = ''
        line_num = this.insert_line(text)
        actor.tell('Line ', line_num, ' added.')


class DeleteTextCmd(EditorSessionCommand):
    """
    .del<range>

    Deletes specified line(s) of text.
    """
    key = 'delete'
    match_prefix = '.d'
    syntax = '{.d|.del|.delete}<range>'
    arg_parsers = {'range': 'range'}

    def run(self, this, actor, range):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type range: tuple of (int, int)
        """
        deleted = this.delete_range(*range)
        show = [this.format_line(*d, caret=-1) for d in deleted]
        actor.msg('\n'.join(show), flags={'raw': True})
        actor.tell('{y---Line(s) deleted. {nInsertion point is at line ',
                   this.caret, '.')


class MoveCaretCmd(EditorSessionCommand):
    """
    .i[^|_]<line>

    Change the insertion point.
    """
    key = 'caret'
    match_prefix = '.i'
    syntax = '{.i|.ins|.insert}[{_|^}]<line>'
    arg_parsers = {'line': 'line'}

    def run(self, this, actor, line):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type line: int
        """
        if 'optset2' in self.parsed_args:
            if self.parsed_args['optset2'] == '_':
                line += 1
        if self.args['line'] == '$':
            line = len(this.lines) + 1
        this.move_caret(line)
        actor.msg(this.list_lines(line - 1, line))


class ListCmd(EditorSessionCommand):
    """
    .list [<range>]

    List text.
    """
    key = 'list'
    match_prefix = '.l'
    syntax = '{.l|.li|.lis|.list}[<range>]'
    arg_parsers = {'range': 'range'}

    def run(self, this, actor, range):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type range: tuple of (int, int)
        """
        if len(this.lines):
            if range is None:
                range = (1, len(this.lines))
            actor.msg(this.list_lines(*range))
        else:
            actor.msg('(no lines)')


class PrintCmd(EditorSessionCommand):
    """
    .print [<range>]

    Print text without line numbers and insertion point indicators.
    """
    key = 'print'
    match_prefix = '.p'
    syntax = '{.p|.pr|.print}[<range>]'
    arg_parsers = {'range': 'range'}

    def run(self, this, actor, range):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type range: tuple of (int, int)
        """
        if range is None:
            range = (1, len(this.lines))
        start, end = range
        actor.msg('\n'.join(this.lines[start - 1:end]))


class EnterCmd(EditorSessionCommand):
    """
    .enter

    Accept lines of input to insert into editor's buffer.
    """
    key = 'enter'
    match_prefix = '.e'
    syntax = '{.e|.ent|.enter}'

    def run(self, this, actor):
        """
        :type this: EditorSession
        :type actor: BaseObject
        """
        actor.read_lines(self.insert_lines)

    def insert_lines(self, lines):
        session = self.session
        for line in lines:
            session.insert_line(line)
        self.actor.tell('{g', len(lines), ' line(s) inserted. ',
                        '{n Insertion point is at line ', session.caret, '.')


class PasteCmd(EditorSessionCommand):
    """
    .paste

    Alias of .enter.
    """
    key = 'paste'
    match_prefix = '.paste'
    syntax = ''


class WhatCmd(EditorSessionCommand):
    """
    .what

    Output a description of what is currently being edited.
    """
    key = 'what'
    match_prefix = '.w'
    syntax = '{.w|.what}'

    def run(self, this, actor):
        """
        :type this: EditorSession
        :type actor: BaseObject
        """
        actor.tell('Currently editing: ', this.description)


class AbortCmd(EditorSessionCommand):
    """
    .abort

    Closes the editor without saving.
    """
    key = 'abort'
    match_prefix = '.abort'

    def run(self, this, actor):
        """
        :type this: EditorSession
        :type actor: BaseObject
        """
        this.owner.terminate_editor_session(this.session_key)
        actor.tell('{yYou have closed the session for editing ',
                   this.description, '.')


class ReplaceCmd(EditorSessionCommand):
    """
    .replace[/i] <search>=<replace> [<range>]

    Replace all instances of 'search' with 'replace' across an optional range.
    """
    key = 'replace'
    match_prefix = '.r'
    syntax = (
        '{.r|.rep|.repl|.replace}\w<search>{=}<replace> [<range>]',
        '{.r/i|.rep/i|.repl/i|.replace/i}\w<search>{=}<replace> [<range>]'
    )
    arg_parsers = {'range': 'range'}
    switch_defaults = {'i': False}

    def run(self, this, actor, search, replace, range):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type search: str
        :type replace: str
        :type range: tuple of int
        """
        case = not self.switches['i']
        if range is None:
            # Insert 1 and insert 2 both perform replace on line 1.
            caret = max(this.caret - 1, 1)
            range = (caret, caret)
        affected = this.substitute(re.escape(search), replace, range,
                                   all=True, case_matters=case)
        total = 0
        for line in affected:
            total += line[2]
        actor.tell(total, " replacements completed.")


class SubstituteCmd(EditorSessionCommand):
    """
    .substitute/<search>/<replace[/[g][i][<range>]]

    Perform regex-based substitution.
    """
    key = 'subst'
    match_prefix = '.subst'
    syntax = '{.subst|.substitute}<subst>'

    def execute(self):
        """Custom parsing!"""
        self.parsed_args = self.parse_subst(self.args['subst'])
        if self.prepare():
            self.before_run()
            self.run(**self.prepare_run_args())
            self.after_run()

    def parse_subst(self, subst):
        sep = subst[0]
        frompat, tostr, laststr = (subst[1:].split(sep) + [''] * 3)[:3]
        flagstr = ''
        while len(laststr) and laststr[0] in ('g', 'i'):
            flagstr += laststr[0]
            laststr = laststr[1:]
        rangestr = laststr
        if not len(rangestr):
            caret = max(self.session.caret - 1, 1)
            line_range = (caret, caret)
        else:
            line_range = self.session.parse_range(rangestr)
        return {
            'all': 'g' in flagstr,
            'case': 'i' not in flagstr,
            'search': frompat,
            'replace': tostr,
            'line_range': line_range
        }

    def run(self, this, actor, search, replace, all, case, line_range):
        """
        :type this: EditorSession
        :type actor: BaseObject
        :type search: str
        :type replace: str
        :type all: bool
        :type case: bool
        :type line_range: tuple of int
        """
        affected = this.substitute(search, replace, line_range=line_range,
                                   all=all, case_matters=case)
        total = 0
        for line in affected:
            total += line[2]
        actor.tell(total, " replacements completed.")


class EditorSession(PersistentSlots):
    """
    An editor session, storing the current state of the editor.
    """
    __slots__ = ('lines', 'caret', 'owner')

    commands = (
        InsertTextCmd,
        DeleteTextCmd,
        MoveCaretCmd,
        ListCmd,
        PrintCmd,
        EnterCmd,
        PasteCmd,
        WhatCmd,
        AbortCmd,
        ReplaceCmd,
        SubstituteCmd
    )

    def __init__(self, owner, preload=''):
        """
        :type owner: EditorSessionHost
        :type preload: str
        """
        #: :type: EditorSessionHost
        self.owner = owner.ref()
        self.lines = preload.splitlines() if isinstance(preload, str) else []
        self.caret = len(self.lines) + 1

    @property
    def parsers(self):
        return {
            'line': self.parse_line,
            'range': self.parse_range,
        }

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

    @property
    def text(self):
        return '\n'.join(self.lines)

    @classmethod
    @obj_utils.memoize()
    def all_commands(cls):
        commands = {}
        for c in obj_utils.descend_mro(cls):
            if issubclass(c, EditorSession) and 'commands' in c.__dict__:
                commands.update({cmd.key: cmd for cmd in c.commands})
        return commands.values()

    def process_command(self, raw, game):
        cmdstr, _, argstr = raw.partition(' ')
        all_commands = self.all_commands()
        exact_matches = [c for c in all_commands if c.exactly_matches(raw)]
        if exact_matches:
            all_commands = exact_matches
        cmd_matches = [c(raw, cmdstr, argstr, game, self, self.owner)
                       for c in all_commands if c.matches(raw)]
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

    def format_line(self, line_num, text, caret=None):
        if caret is None:
            caret = self.caret
        if caret == (line_num + 1):
            p = s = '_'
        elif caret == line_num:
            p = s = '^'
        else:
            p = ' '
            s = ':'
        pad = len(str(len(self.lines)))
        fmt = '{p}{n:>%d}{s} {t}' % pad
        return fmt.format(n=line_num, t=text, p=p, s=s)

    def list_lines(self, start, end, lines=None):
        lines = lines or self.lines
        start = max(1, start)
        end = min(len(lines), end)
        show = [self.format_line(n + start, t)
                for n, t in enumerate(lines[start - 1:end])]
        if end == len(lines) and self.caret > end:
            show.append('^' * (len(str(end)) + 2))
        return '\n'.join(show)

    def parse_line(self, input):
        try:
            if input == '$':
                return len(self.lines)
            elif input == '.':
                return self.caret
            elif input.startswith('^'):
                return int(input[1:])
            elif input.startswith('_'):
                return int(input[1:]) + 1
            else:
                return int(input)
        except ValueError:
            raise InvalidLineSyntax("Invalid line format: %s" % input)

    range_re = re.compile(
        '(?P<start>\$|\.|(?:[_^]?\d+))(?: *- *(?P<end>\$|\.|(?:[_^]?\d+)))?')

    def parse_range(self, input):
        m = self.range_re.match(input)
        if m:
            start = self.parse_line(m.group('start'))
            _end = m.group('end')
            end = self.parse_line(_end) if _end is not None else start
            return (start, end) if start <= end else (end, start)
        else:
            raise InvalidRangeSyntax("Invalid range: %s" % input)

    def which_line(self, line_num=None):
        """
        Given an optional explicit number, determine which line to act on.
        """
        return line_num if line_num is not None else self.caret

    def insert_line(self, text, line_num=None, update_caret=True):
        """
        Insert a line of text at the specified line number. Defaults to the
        location of the caret.

        Defaults to moving the caret to just after the newly inserted line.

        :param text: The text to insert.
        :type text: str

        :param line_num: The line number to be inserted at.
        :type line_num: int

        :return: The number of the line that was inserted.
        :rtype: int
        """
        line_num = self.which_line(line_num)
        self.lines.insert(line_num - 1, ''.join(text.splitlines()))
        if update_caret:
            self.move_caret(line_num + 1)
        return line_num

    def delete_line(self, line_num=None, update_caret=True):
        """
        Delete the specified line (or the line above the caret).

        Optionally move caret to where delete occurred. If caret is past where
        delete happened, caret will be updated regardless of this parameter.

        :param line_num: The line to delete.
        :param update_caret: Whether or not to move the caret to deleted line.

        :return: The line number that was deleted, and the text that was there.
        :rtype: tuple of (int, str)
        """
        line_num = self.which_line(line_num)
        text = self.lines[line_num - 1]
        del self.lines[line_num - 1]
        if update_caret or self.caret > len(self.lines):
            self.move_caret(line_num)
        return line_num, text

    def delete_range(self, start, end):
        """
        Delete a series of lines.

        :param start: First line to delete.
        :param end: Last line to delete.
        :return: Tuples of the line number and text for each deleted line.
        """
        deleted = tuple(self.delete_line(n) for n in range(end, start - 1, -1))
        return reversed(deleted)

    def move_caret(self, line_num):
        """
        Move the caret.

        :param line_num: The new position of the caret.
        :return: The previous position of the caret.
        """
        previous = self.caret
        self.caret = line_num
        return previous

    def substitute(self, pattern, replacement, line_range=None, all=False,
                   case_matters=True):
        """
        Perform a regular-expression replacement across the specified range.

        :param pattern: A regular expression string whose matches to replace.
        :type: str

        :param replacement: The regex replacement string.
        :type: str

        :param line_range: A tuple of the first and last line to search.
        :type: tuple or None

        :param all: Whether to replace all occurrences on each line or not. If
            False, then only replace first occurrence on each line.
        :type: bool

        :param case_matters: Whether or not case matters.
        :type: bool

        :return: A list of tuples of the line number, previous text, and the
            number of replacements performed on that line for the each affected
            line.
        :rtype: list of tuple of (int, str, int)
        """
        if line_range is None:
            start = end = self.caret
        else:
            start, end = line_range
        flags = 0 if case_matters else re.IGNORECASE
        count = 0 if all else 1
        regex = re.compile(pattern, flags=flags)
        old_lines = []
        for index in range(start - 1, end):
            old_line = self.lines[index]
            self.lines[index], n = regex.subn(replacement, self.lines[index],
                                              count=count)
            old_lines.append((index + 1, old_line, n))
        return old_lines
