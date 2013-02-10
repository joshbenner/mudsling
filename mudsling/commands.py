import logging
import shlex
import inspect

import inflect

from mudsling.utils import string
from mudsling.utils.syntax import Syntax, SyntaxParseError


prepositions = (
    ('with', 'using'),
    ('at', 'to'),
    ('in front of',),
    ('in', 'inside', 'into'),
    ('on top of', 'on', 'onto', 'upon'),
    ('out of', 'from inside', 'from'),
    ('over',),
    ('through',),
    ('under', 'underneath', 'beneath'),
    ('behind',),
    ('beside',),
    ('for', 'about'),
    ('is',),
    ('as',),
    ('off', 'off of'),
)


class Command(object):
    """
    Base class for command objects.

    Command classes describe the command and perform matching of the command
    against input. Commands are only instantiated when they are run, so the
    command may feel free to use the command instance as it wishes.

    @cvar required_perm: An object must have this perm to use this command.
    @cvar aliases: Regular expressions that can match to trigger the command.
    @cvar syntax: String representation of the command's syntax that is parse-
        able by mudsling.utils.syntax.Syntax.
    @cvar require_syntax_match: If True, then the command will only match if
        the syntax parses the argstr successfully.
    @cvar valid_args: Dictionary with keys matching args keys and values giving
        hints about how the validator should validate the arg values.

    @ivar obj: The object hosting this command.
    @ivar raw: The raw command-line input
    @ivar cmdstr: The command part of the input string.
    @ivar argstr: The argument part of the input string.
    @ivar argwords: A list of words (grouped by quotes) in the argstr.
    @ivar args: The result of parsing the arguments.
    @ivar parsed: Un-modified parsed argstr.
    @ivar actor: The object responsible for the input leading to execution.
    @ivar game: Handy reference to the game object.
    """

    aliases = ()
    syntax = ""
    #: @type: Syntax
    _syntax = None
    require_syntax_match = False

    valid_args = {}

    required_perm = None

    #: @type: mudsling.objects.BaseObject
    obj = None

    #: @type: mudsling.objects.BaseObject
    actor = None

    #: @type: str
    raw = None
    cmdstr = None
    argstr = None

    #: @type: list
    argwords = []

    #: @type: dict
    args = {}
    parsed = {}

    #: @type: mudsling.core.MUDSling
    game = None

    @classmethod
    def name(cls):
        if len(cls.aliases) > 0:
            return cls.aliases[0]
        return 'ERROR NO CMD ALIAS'

    @classmethod
    def checkAccess(cls, actor):
        """
        Determine if an object is allowed to use this command.

        @param actor: The object that wants to use this command.
        @type actor: mudsling.objects.BaseObject

        @rtype: bool
        """
        if cls.required_perm is not None:
            return actor.hasPerm(cls.required_perm)
        return True

    @classmethod
    def matches(cls, cmdstr):
        """
        Determine if this command matches the command portion of the input.

        @param cmdstr: The command part of the raw input.
        @type cmdstr: str

        @rtype: bool
        """
        return cmdstr in cls.aliases

    @classmethod
    def _compileSyntax(cls):
        try:
            cls._syntax = Syntax(cls.syntax)
        except SyntaxParseError as e:
            logging.error("Cannot parse %s syntax: %s"
                          % (cls.name(), e.message))
            return False

    def matchSyntax(self, argstr):
        """
        Determine if the input matches the command syntax.
        @rtype: bool
        """
        if self._syntax is None and self.syntax:
            self._compileSyntax()

        if not self.syntax and argstr == '':
            return True

        parsed = self._syntax.parse(argstr)
        if parsed:
            self.args = parsed
            # Check for 'this' in any of the validators.
            for argName, valid in self.valid_args.iteritems():
                if valid == 'this':
                    matches = self.actor.matchObject(parsed[argName])
                    if len(matches) != 1 or matches[0] != self.obj:
                        return False
            return True
        return False

    @classmethod
    def getSyntax(cls):
        """
        Return just the syntax portion of the command class's docstring.

        @return: Syntax string
        @rtype: str
        """
        trimmed = string.trimDocstring(cls.__doc__)
        syntax = []
        for line in trimmed.splitlines():
            if line == "":
                break
            syntax.append(line)
        return '\n'.join(syntax)

    def __init__(self, raw, cmdstr, argstr, game=None, obj=None, actor=None):
        """
        @param raw: The raw input.
        @type raw: str

        @param cmdstr: The command part of the input.
        @type cmdstr: str

        @param argstr: The argument part of the input.
        @type argstr: str

        @param game: Reference to the game instance.
        @type game: mudsling.core.MUDSling

        @param obj: The object hosting the command.
        @type obj: mudsling.objects.BaseObject or mudsling.storage.ObjRef

        @param actor: The object executing this command.
        @type actor: mudsling.objects.BaseObject or mudsling.storage.ObjRef
        """
        self.raw = raw
        self.cmdstr = cmdstr
        self.argstr = argstr
        self.argwords = shlex.split(argstr)
        self.game = game
        self.obj = obj
        self.actor = actor

    def execute(self):
        """
        Execution entry point for the command. The object system should call
        this once it has decided to run the command.
        """
        if self.prepare():
            self.run(self.obj, self.actor, self.args)

    def processArgs(self):
        """
        Process args against valid_args. This is primarily a way to avoid
        matching and validating the correct type for every command that need to
        do so.

        valid_args value options:
          - 'this': Actor object match for this arg yields the command's host
            object. This is handled during syntax parsing/matching.
          - Class: command will match object with actor and validate the result
            is an object instance descendant of the specified class.

        Validated argument values will be replaced by their validated values in
        the args dictionary.
        """
        args = self.args
        for argName, valid in self.valid_args.iteritems():
            if argName not in args:
                continue
            if inspect.isclass(valid):
                argVal = args[argName]
                matches = self.actor.matchObject(argVal)
                if self.matchFailed(matches, argVal):
                    args[argName] = None
                    continue
                match = matches[0]
                if isinstance(match, valid):
                    args[argName] = match
                else:
                    args[argName] = TypeError

    def prepare(self):
        """
        Here a command can perform any isolated parsing of the input or other
        preparation it wishes. This hook is called before command execution. If
        this returns a non-true value, then command is not run.

        This is a handy place to do any complex (and possibly re-usable)
        custom parsing of the command input.

        @rtype: bool
        """
        return True

    def run(self, this, actor, args):
        """
        This is where the magic happens.
        """

    def syntaxHelp(self):
        """
        Return a string to show to a player to help them understand the syntax
        of the command. Useful to output when a command is used incorrectly.

        The default implementation just outputs the command's syntax.
        @return: str
        """
        out = []
        for i, line in enumerate(self.__class__.getSyntax().splitlines()):
            if i == 0:
                line = "Syntax: " + line
            else:
                line = "        " + line
            out.append(line)
        return '\n'.join(out)

    def matchFailed(self, matches, search=None, searchFor=None, show=False):
        """
        Utility method to handled failed matches. Will inform the actor if a
        search for a single match has failed and return True if the search
        failed.

        @param matches: The result of the match search.
        @type matches: list

        @param search: The string used to search.
        @type search: str

        @param searchFor: A string describing what type of thing was being
            searched for. This should be the singular form of the word.
        @type searchFor: str

        @param show: If true, will show the list of possible matches in the
            case of an ambiguous match.
        @type show: bool

        @return: True if the searched failed, False otherwise.
        @rtype: bool
        """
        p = inflect.engine()

        if len(matches) == 1:
            return False
        elif len(matches) > 1:
            if search is not None:
                if searchFor is not None:
                    msg = ("Multiple %s match '%s'"
                           % (p.plural(searchFor), search))
                else:
                    msg = "Multiple matches for '%s'" % search
            else:
                if searchFor is not None:
                    msg = "Multiple %s found" % p.plural(searchFor)
                else:
                    msg = "Multiple matches"
            if show:
                msg += ': ' + string.english_list(matches)
            else:
                msg += '.'
        else:
            if search is not None:
                if searchFor is not None:
                    msg = "No %s called '%s' was found." % (searchFor, search)
                else:
                    msg = "No '%s' was found." % search
            else:
                if searchFor is not None:
                    msg = "No matching %s found." % p.plural(searchFor)
                else:
                    msg = "No match found."

        self.actor.msg(msg)
        return True


def makeCommandList(obj):
    """
    Return a list of command classes provided by an object (ie: a module).
    @rtype: list
    """
    commands = []
    for name in obj.__dict__:
        cmd = getattr(obj, name)
        if inspect.isclass(cmd) and issubclass(cmd, Command):
            if not cmd in commands:
                commands.append(cmd)
    return commands


def allCommands(*objects):
    """
    Takes objects (including modules), and pulls out all command classes
    provided in their members and flattens them into a single command list.
    @rtype: list
    """
    commands = []
    for o in objects:
        for cmd in makeCommandList(o):
            if not cmd in commands:
                commands.append(cmd)
    return commands
