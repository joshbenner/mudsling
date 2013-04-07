import logging
import shlex
import inspect

import zope.interface

from mudsling.storage import StoredObject
from mudsling.match import match_failed
from mudsling.utils import string
from mudsling.utils.syntax2 import Syntax, SyntaxParseError
from mudsling.utils.sequence import dictMerge
from mudsling import parsers
from mudsling.errors import CommandInvalid
from mudsling import locks


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

    @cvar runLock: Object must satisfy lock to execute command.
    @cvar aliases: Regular expressions that can match to trigger the command.
    @cvar syntax: String representation of the command's syntax that is parse-
        able by mudsling.utils.syntax.Syntax.
    @cvar arg_parsers: Dictionary with keys matching args keys and values
        giving hints about how the validator should parse the arg values. This
        is also used by the syntax matching phase for arguments that should
        resolve to the object providing the command ('this').
    @cvar switch_parsers: Just like arg_parsers, but for switches.
    @cvar switch_defaults: Default values for switches.

    @ivar obj: The object hosting this command.
    @ivar raw: The raw command-line input
    @ivar cmdstr: The command part of the input string.
    @ivar switchstr: The unparsed switch segment of the command.
    @ivar argstr: The argument part of the input string.
    @ivar argwords: A list of words (grouped by quotes) in the argstr.
    @ivar args: The raw input for the arguments.
    @ivar parsed_args: The fully-parsed values for the arguments.
    @ivar switches: Parsed switches.
    @ivar actor: The object responsible for the input leading to execution.
    @ivar game: Handy reference to the game object.
    """

    aliases = ()
    syntax = ""
    #: @type: list
    _syntax = None

    arg_parsers = {}
    switch_parsers = {}
    switch_defaults = {}

    lock = locks.NonePass  # Commands are restricted by default.

    #: @type: mudsling.objects.BaseObject
    obj = None

    #: @type: mudsling.objects.BaseObject
    actor = None

    #: @type: str
    raw = None
    cmdstr = None
    switchstr = None
    argstr = None

    #: @type: list
    argwords = []

    #: @type: dict
    args = {}
    parsed_args = {}
    switches = {}

    #: @type: mudsling.core.MUDSling
    game = None

    @classmethod
    def name(cls):
        if len(cls.aliases) > 0:
            return cls.aliases[0]
        return 'ERROR NO CMD ALIAS'

    @classmethod
    def checkAccess(cls, obj, actor):
        """
        Determine if an object is allowed to use this command.

        @param actor: The object that wants to use this command.
        @type actor: mudsling.objects.BaseObject

        @rtype: bool
        """
        if isinstance(cls.lock, basestring):
            cls.lock = locks.Lock(cls.lock)
        return cls.lock.eval(obj, actor)

    @classmethod
    def matches(cls, cmdstr):
        """
        Determine if this command matches the command portion of the input.

        @param cmdstr: The command part of the raw input.
        @type cmdstr: str

        @rtype: bool
        """
        return cmdstr.split('/')[0] in cls.aliases

    @classmethod
    def _compileSyntax(cls):
        cls._syntax = []
        try:
            if isinstance(cls.syntax, basestring):
                syntaxes = (cls.syntax,)
            else:
                syntaxes = cls.syntax
            for syntax in syntaxes:
                cls._syntax.append(Syntax(syntax))
        except SyntaxParseError as e:
            logging.error("Cannot parse %s syntax: %s"
                          % (cls.name(), e.message))
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
        self.cmdstr, sep, self.switchstr = cmdstr.partition('/')
        self.cmdstr = cmdstr
        self.argstr = argstr
        self.argwords = shlex.split(argstr)
        self.game = game
        self.obj = obj
        self.actor = actor

    def matchSyntax(self, argstr):
        """
        Determine if the input matches the command syntax.
        @rtype: bool
        """
        if self._syntax is None:
            self._compileSyntax()

        parsed = {}
        for syntax in self._syntax:
            parsed = syntax.parse(argstr)
            if isinstance(parsed, dict):
                break
        if parsed:
            self.args = parsed
            # Check for 'this' in any of the validators.
            for argName, valid in self.arg_parsers.iteritems():
                if valid == 'this':
                    matches = self.actor.matchObject(parsed[argName])
                    if len(matches) != 1 or matches[0] != self.obj:
                        return False
            return True
        return False

    def failedCommandMatchHelp(self):
        """
        This method is called if this command was matched by name, but not by
        syntax, and the command parser is asking the command for some help to
        guide the user.

        If the command has nothing to say, just return False.
        """
        return self.syntaxHelp()

    def execute(self):
        """
        Execution entry point for the command. The object system should call
        this once it has decided to run the command.
        """
        switches = self.parseArgs(self.parseSwitches(self.switchstr),
                                  self.switch_parsers)
        self.switches = dictMerge(self.switch_defaults, switches)
        self.parsed_args = self.parseArgs(self.args, self.arg_parsers)
        if self.prepare():
            self.run(self.obj, self.actor, self.parsed_args)

    def parseSwitches(self, switchstr):
        """
        Parses raw switch string into key/val string pairs. No value resolution
        beyond just getting the key and value strings is done.

        @param switchstr: The raw switch string.
        @rtype: C{dict}
        """
        switches = {}
        sp = self.switch_parsers
        defaults = self.switch_defaults
        for switch in switchstr.split('/'):
            if not switch:
                continue
            key, sep, val = switch.partition('=')
            if key not in sp and key not in defaults:
                raise CommandInvalid(msg="Unknown switch: %s" % key)
            if val == '':  # Set switch to true if it is present without val.
                if key in sp and issubclass(sp[key], parsers.BoolStaticParser):
                    val = sp[key].trueVals[0]
                else:
                    val = True
            switches[key] = val
        return switches

    def parseArgs(self, args, arg_parsers):
        """
        Process args against arg_parsers.

        The first phase in command execution is to parse the arguments. This
        can be done simply and cleanly by defining parser information for each
        argument in arg_parsers rather than parsing the args in the run()
        method. However, you are not required to do so.

        arg_parsers value options:
          - 'this': Actor object match for this arg yields the command's host
            object. This is handled during syntax parsing/matching.
          - Subclass of L{mudsling.parsers.StaticParser}: Use a StaticParser
            class to translate the input to a value.
          - Class descendant from L{StoredObject}: command will match object
            with actor and validate the result is an object instance descendant
            of the specified class.
          - callable: Passes user input to the callable and stores the result.
            Note that this works with int, float, list, tuple, etc.
          - tuple: First element expected to be callable. Will pass input
            followed by any other tuple elements as the arguments for callbale.

        Validated argument values will be replaced by their validated values in
        the args dictionary.
        """
        parsed = dict(args)
        for argName, valid in arg_parsers.iteritems():
            if argName not in args or valid == 'this' or args[argName] is None:
                continue
            elif isinstance(valid, parsers.Parser):
                parsed[argName] = valid.parse(args[argName], obj=self.actor)
            elif (inspect.isclass(valid)
                  and issubclass(valid, parsers.StaticParser)):
                parsed[argName] = valid.parse(args[argName])
            elif inspect.isclass(valid) and issubclass(valid, StoredObject):
                argVal = args[argName]
                matches = self.actor.matchObject(argVal)
                if self.matchFailed(matches, argVal):
                    parsed[argName] = None
                    continue
                match = matches[0]
                if match.isValid(valid):
                    parsed[argName] = match
                else:
                    parsed[argName] = TypeError("Object is wrong type.")
            elif callable(valid) or isinstance(valid, tuple):
                if isinstance(valid, tuple):
                    callback = valid[0]
                    cb_args = valid[1:]
                else:
                    callback = valid
                    cb_args = ()
                try:
                    parsed[argName] = callback(args[argName], *cb_args)
                except Exception as e:
                    parsed[argName] = e
        return parsed

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
        if self.aliases:
            msg = "The '%s' command" % self.aliases[0]
        else:
            msg = "That command"
        raise NotImplementedError(msg)

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
                line = "{ySyntax: {c" + line
            else:
                line = "        {c" + line
            out.append(line)
        return '\n'.join(out)

    def matchFailed(self, matches, search=None, searchFor=None, show=False):
        """
        Utility method to handled failed matches. Will inform the actor if a
        search for a single match has failed and return True if the search
        failed.

        @see: L{mudsling.match.match_failed}

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
        msg = match_failed(matches, search=search, searchFor=searchFor,
                           show=show)
        if msg:
            self.actor.msg(msg)
        return True if msg else False

    def _err(self, msg=None):
        """
        Quick and handy way to generate an error inside a command.

        Example:
            raise self._err("That makes no sense!")
        """
        return CommandInvalid(cmdline=self.raw, msg=msg)


class IHasCommands(zope.interface.Interface):
    """
    Provides public and/or proviate commands and functions to find them.
    """
    private_commands = zope.interface.Attribute(
        """List of commands available only to self.""")
    public_commands = zope.interface.Attribute(
        """List of commands available to other objects.""")

    def commandsFor(actor):
        """
        Return a list of commands available to the specified actor.
        """


def makeCommandList(obj):
    """
    Return a list of command classes provided by an object (ie: a module).
    @rtype: list
    """
    commands = []
    for name in obj.__dict__:
        c = getattr(obj, name)
        if inspect.isclass(c) and issubclass(c, Command) and c != Command:
            if not c in commands:
                commands.append(c)
    return commands


def allCommands(*objects):
    """
    Takes objects (including modules), and pulls out all command classes
    provided in their members and flattens them into a single command list.
    @rtype: list
    """
    commands = []
    for o in objects:
        if inspect.isclass(o) and issubclass(o, Command):
            commands.append(o)
            continue
        for cmd in makeCommandList(o):
            if not cmd in commands:
                commands.append(cmd)
    return commands
