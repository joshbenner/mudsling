import logging
import inspect

import zope.interface

from mudsling.storage import StoredObject
from mudsling.match import match_failed
from mudsling.utils import string
from mudsling.utils.syntax2 import Syntax, SyntaxParseError
from mudsling.utils.sequence import dict_merge
from mudsling import parsers
import mudsling.errors
from mudsling import locks

from mudsling import utils
import mudsling.utils.object


class CommandSet(object):
    """
    A compiled set of commands used for matching of a command.

    This class is used rather than a simple list so that child classes can
    includes commands whose key matches that of another command included by an
    ancestor class, thereby hiding the ancestor's command and replacing it with
    the descendant's command.

    :ivar commands: A map of key:command pairs.
    """
    commands = {}

    def __init__(self, commands=None, container=None):
        """
        Create a new command set.

        :param commands: Iterable of command classes to initialize with.
        :type commands: dict or list or tuple or CommandSet

        :param container: An object whose members include command classes that
            are to be added to this CommandSet's commands. Can be a module.
        :type container: object
        """
        self.commands = {}
        if commands is not None:
            self.add_commands(commands)
        if container is not None:
            self.add_commands(all_commands(container))

    def add_command(self, cmd):
        """
        Adds a command to the set.

        If a command with the same key is already in the set, it is replaced.

        :param cmd: The command CLASS to add.
        :type cmd: Command
        """
        if cmd.__dict__.get('abstract', False):
            return
        try:
            self.commands[cmd.key] = cmd
        except Exception as e:
            logging.error("Failed loading command %r: %s" % (cmd, e.message))

    def add_commands(self, commands):
        if isinstance(commands, CommandSet):
            self.commands.update(commands.commands)
        else:
            for cmd in commands:
                self.add_command(cmd)

    def match(self, cmd_name, host, actor):
        matches = []
        for cmdcls in self.commands.itervalues():
            if cmdcls.matches(cmd_name) and cmdcls.check_access(host, actor):
                matches.append(cmdcls)
        return matches

    def command_parser(self, raw_input, host, actor, game):
        cmd_and_switches, _, argstr = raw_input.partition(' ')
        cmdstr, _, switchstr = cmd_and_switches.partition('/')
        name_matches = self.match(cmdstr, host, actor)
        instances = [c(raw_input, cmdstr, argstr, game, host, actor)
                     for c in name_matches]
        syntax_matches = [c for c in instances if c.match_syntax(argstr)]
        if len(syntax_matches) > 1:
            raise mudsling.errors.AmbiguousMatch(msg="Ambiguous Command",
                                                 query=raw_input,
                                                 matches=syntax_matches)
        elif not syntax_matches and name_matches:
            m = '\n'.join(c.failed_command_match_help() for c in instances)
            raise mudsling.errors.CommandError(msg=m)
        elif not syntax_matches:
            return None
        else:
            return syntax_matches[0]


class Command(object):
    """
    Base class for command objects.

    Command classes describe the command and perform matching of the command
    against input. Commands are only instantiated when they are run, so the
    command may feel free to use the command instance as it wishes.

    :cvar lock: Object must satisfy lock to execute command.
    :cvar aliases: Regular expressions that can match to trigger the command.
    :cvar syntax: String representation of the command's syntax that is parse-
        able by mudsling.utils.syntax.Syntax.
    :cvar arg_parsers: Dictionary with keys matching args keys and values
        giving hints about how the validator should parse the arg values. This
        is also used by the syntax matching phase for arguments that should
        resolve to the object providing the command ('this').
    :cvar switch_parsers: Just like arg_parsers, but for switches.
    :cvar switch_defaults: Default values for switches.

    :ivar obj: The object hosting this command.
    :ivar raw: The raw command-line input
    :ivar cmdstr: The command part of the input string.
    :ivar switchstr: The unparsed switch segment of the command.
    :ivar argstr: The argument part of the input string.
    :ivar argwords: A list of words (grouped by quotes) in the argstr.
    :ivar args: The raw input for the arguments.
    :ivar parsed_args: The fully-parsed values for the arguments.
    :ivar switches: Parsed switches.
    :ivar actor: The object responsible for the input leading to execution.
    :ivar game: Handy reference to the game object.
    """
    aliases = ()
    syntax = ""
    #: :type: list
    _syntax = None

    arg_parsers = {}
    switch_parsers = {}
    switch_defaults = {}

    lock = locks.none_pass  # Commands are restricted by default.

    abstract = False  # Flag as abstract to avoid populating command lists.

    #: :type: mudsling.objects.BaseObject
    obj = None

    #: :type: mudsling.objects.BaseObject
    actor = None

    #: :type: str
    raw = None
    cmdstr = None
    switchstr = None
    argstr = None

    #: :type: list
    argwords = []

    #: :type: dict
    args = {}
    parsed_args = {}
    switches = {}

    #: :type: mudsling.core.MUDSling
    game = None

    @utils.object.ClassProperty
    @classmethod
    def key(cls):
        """
        By default, the key of a command is its first alias. This can be
        overridden by specifically setting key on the child class.
        """
        try:
            return cls.aliases[0]
        except IndexError:
            raise Exception("Invalid command key.")

    @classmethod
    def name(cls):
        if len(cls.aliases) > 0:
            return cls.aliases[0]
        return 'ERROR NO CMD ALIAS'

    @classmethod
    def check_access(cls, obj, actor):
        """
        Determine if an object is allowed to use this command.

        :param actor: The object that wants to use this command.
        :type actor: mudsling.objects.BaseObject

        :rtype: bool
        """
        if isinstance(cls.lock, basestring):
            cls.lock = locks.Lock(cls.lock)
        return cls.lock.eval(obj, actor)

    @classmethod
    def matches(cls, cmdstr):
        """
        Determine if this command matches the command portion of the input.

        :param cmdstr: The command part of the raw input.
        :type cmdstr: str

        :rtype: bool
        """
        return cmdstr.split('/')[0] in cls.aliases

    @classmethod
    def _compile_syntax(cls):
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
    def get_syntax(cls):
        """
        Return just the syntax portion of the command class's docstring.

        :return: Syntax string
        :rtype: str
        """
        trimmed = string.trim_docstring(cls.__doc__)
        syntax = []
        for line in trimmed.splitlines():
            if line == "":
                break
            syntax.append(line)
        return '\n'.join(syntax)

    def __init__(self, raw, cmdstr, argstr, game=None, obj=None, actor=None,
                 parse=False):
        """
        :param raw: The raw input.
        :type raw: str

        :param cmdstr: The command part of the input.
        :type cmdstr: str

        :param argstr: The argument part of the input.
        :type argstr: str

        :param game: Reference to the game instance.
        :type game: mudsling.core.MUDSling

        :param obj: The object hosting the command.
        :type obj: mudsling.objects.BaseObject or mudsling.storage.ObjRef

        :param actor: The object executing this command.
        :type actor: mudsling.objects.BaseObject or mudsling.storage.ObjRef

        :param parse: Whether or not to parse the syntax immediately.
        :type parse: bool
        """
        self.raw = raw
        self.cmdstr, sep, self.switchstr = cmdstr.partition('/')
        self.argstr = argstr
        try:
            self.argwords = utils.string.split_quoted_words(argstr)
        except ValueError:
            self.argwords = argstr.split(' ')
        self.game = game
        self.obj = obj
        self.actor = actor
        if parse:
            self.match_syntax(argstr)

    def match_syntax(self, argstr):
        """
        Determine if the input matches the command syntax.
        :rtype: bool
        """
        if '_syntax' not in self.__class__.__dict__:
            self._compile_syntax()

        parsed = {}
        for syntax in self._syntax:
            parsed = syntax.parse(argstr)
            if isinstance(parsed, dict):
                break
        if parsed:
            self.args = parsed
            # Check for 'this' in any of the validators.
            for argName, valid in self.arg_parsers.iteritems():
                if isinstance(valid, str) and valid.lower() == 'this':
                    matches = self.actor.match_object(parsed[argName])
                    if self.obj not in matches:
                        return False
                    elif len(matches) > 1:
                        msg = "Multiple matches for '%s': %s"
                        msg %= (parsed[argName],
                                string.english_list(
                                    matches,
                                    formatter=lambda o: self.actor.name_for(o)
                                ))
                        raise mudsling.errors.AmbiguousMatch(
                            msg=msg,
                            query=parsed[argName],
                            matches=matches
                        )
            return True
        return False

    def failed_command_match_help(self):
        """
        This method is called if this command was matched by name, but not by
        syntax, and the command parser is asking the command for some help to
        guide the user.

        If the command has nothing to say, just return False.
        """
        return self.syntax_help()

    def execute(self):
        """
        Execution entry point for the command. The object system should call
        this once it has decided to run the command.
        """
        switches = self.parse_args(self.parse_switches(self.switchstr),
                                   self.switch_parsers)
        self.switches = dict_merge(self.switch_defaults, switches)
        self.parsed_args = self.parse_args(self.args, self.arg_parsers)
        if self.prepare():
            self.before_run()
            self.run(**self.prepare_run_args())
            self.after_run()

    def run_args_map(self):
        return {
            'this': self.obj,
            'actor': self.actor,
            'args': self.parsed_args,
            'switches': self.switches,
        }

    def prepare_run_args(self, extra=None, method='run'):
        """
        Prepare the arguments to be passed to run, matching parsed args to
        argument names if possible.

        :return: The arguments to pass to run.
        :rtype: dict
        """
        args = self.run_args_map()
        if extra is not None:
            args.update(extra)
        args.update((k, v) for k, v in self.parsed_args.iteritems()
                    if k not in args)
        spec = inspect.getargspec(
            getattr(self, method) if isinstance(method, basestring)
            else method)
        if spec.keywords is not None:
            # If the method accepts all keywords, just pass them all in.
            return args
        # Otherwise, only pass keyword arguments listed in the arglist.
        return dict((k, v) for k, v in args.iteritems() if k in spec.args)

    def before_run(self):
        """Commands can fire additional logic before running."""
        pass

    def after_run(self):
        """Commands can fire additional logic after running."""
        pass

    def parse_switches(self, switchstr):
        """
        Parses raw switch string into key/val string pairs. No value resolution
        beyond just getting the key and value strings is done.

        :param switchstr: The raw switch string.
        :rtype: dict
        """
        switches = {}
        sp = self.switch_parsers
        defaults = self.switch_defaults
        for switch in switchstr.split('/'):
            if not switch:
                continue
            key, sep, val = switch.partition('=')
            if key not in sp and key not in defaults:
                raise mudsling.errors.CommandInvalid(
                    msg="Unknown switch: %s" % key)
            if val == '':  # Set switch to true if it is present without val.
                if key in sp and issubclass(sp[key], parsers.BoolStaticParser):
                    val = sp[key].true_vals[0]
                else:
                    val = True
            switches[key] = val
        return switches

    def parse_args(self, args, arg_parsers):
        """
        Process args against arg_parsers.

        The first phase in command execution is to parse the arguments. This
        can be done simply and cleanly by defining parser information for each
        argument in arg_parsers rather than parsing the args in the run()
        method. However, you are not required to do so.

        arg_parsers value options:
          - 'this': Actor object match for this arg yields the command's host
            object. This is handled during syntax parsing/matching.
          - Subclass of mudsling.parsers.StaticParser: Use a StaticParser
            class to translate the input to a value.
          - Class descendant from StoredObject: command will match object
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
            if valid == 'this':
                # This is matched during an earlier phase.
                parsed[argName] = self.obj
            if argName not in args or args[argName] is None:
                continue
            else:
                parsed[argName] = self.parse_arg(args[argName], valid)
        return parsed

    def parse_arg(self, input, parser):
        """
        Parse a single argument.

        :param input: The input to parse.
        :param parser: A parser class, object, or other valid specification.
        """
        val = input
        if isinstance(parser, str) and parser.lower() == 'this':
            val = self.obj
        elif isinstance(parser, parsers.Parser):
            val = parser.parse(input, actor=self.actor)
        elif (inspect.isclass(parser)
              and issubclass(parser, parsers.StaticParser)):
            val = parser.parse(input)
        elif inspect.isclass(parser) and issubclass(parser, StoredObject):
            matches = self.actor.match_object(input)
            if self.match_failed(matches, input):
                val = None
            else:
                match = matches[0]
                if match.is_valid(parser):
                    val = match
                else:
                    val = TypeError("Object is wrong type.")
        elif callable(parser) or isinstance(parser, tuple):
            if isinstance(parser, tuple):
                callback = parser[0]
                cb_args = parser[1:]
            else:
                callback = parser
                cb_args = ()
            val = callback(input, *cb_args)
        return val

    def arg(self, name):
        return self.parsed_args[name]

    def switch(self, name):
        return self.switches[name]

    def prepare(self):
        """
        Here a command can perform any isolated parsing of the input or other
        preparation it wishes. This hook is called before command execution. If
        this returns a non-true value, then command is not run.

        This is a handy place to do any complex (and possibly re-usable)
        custom parsing of the command input.

        :rtype: bool
        """
        return True

    def run(self, **kw):
        """
        This is where the magic happens.
        """
        if self.aliases:
            msg = "The '%s' command" % self.aliases[0]
        else:
            msg = "That command"
        raise NotImplementedError(msg)

    def syntax_help(self):
        """
        Return a string to show to a player to help them understand the syntax
        of the command. Useful to output when a command is used incorrectly.

        The default implementation just outputs the command's syntax.
        :return: str
        """
        out = []
        for i, line in enumerate(self.__class__.get_syntax().splitlines()):
            if i == 0:
                line = "{ySyntax: {c" + line
            else:
                line = "        {c" + line
            out.append(line)
        return '\n'.join(out)

    def match_failed(self, matches, search=None, search_for=None, show=False):
        """
        Utility method to handled failed matches. Will inform the actor if a
        search for a single match has failed and return True if the search
        failed.

        See: :func:`mudsling.match.match_failed`

        :param matches: The result of the match search.
        :type matches: list

        :param search: The string used to search.
        :type search: str

        :param search_for: A string describing what type of thing was being
            searched for. This should be the singular form of the word.
        :type search_for: str

        :param show: If true, will show the list of possible matches in the
            case of an ambiguous match.
        :type show: bool

        :return: True if the searched failed, False otherwise.
        :rtype: bool
        """
        msg = match_failed(matches, search=search, search_for=search_for,
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
        return mudsling.errors.CommandInvalid(cmdline=self.raw, msg=msg)


class SwitchCommandHost(Command):
    """
    A special type of command that has other sub-commands attached to it, which
    are activated by the host command's switches.
    """
    default_switch = None
    subcommands = ()

    @classmethod
    @mudsling.utils.object.memoize()
    def _command_set(cls):
        """:rtype: CommandSet"""
        return CommandSet(cls.subcommands)

    def match_syntax(self, argstr):
        # Assume syntax matches, and let subcommands actually parse.
        return True

    def execute(self):
        # Don't do any parsing, since subcommands will handle that.
        if self.prepare():
            self.before_run()
            self.run(self.obj, self.actor)
            self.after_run()

    def before_run(self):
        if not self.switchstr and self.default_switch is not None:
            self.switchstr = self.default_switch

    def run(self, obj, actor):
        raw = ('%s %s' % (self.switchstr, self.argstr)).strip()
        subcmd = self._command_set().command_parser(raw, obj, actor, self.game)
        if subcmd is not None:
            subcmd.execute()
        else:
            raise mudsling.errors.CommandInvalid()


class IHasCommands(zope.interface.Interface):
    """
    Provides public and/or proviate commands and functions to find them.
    """
    private_commands = zope.interface.Attribute(
        """List of commands available only to self.""")
    public_commands = zope.interface.Attribute(
        """List of commands available to other objects.""")

    def commands_for(actor):
        """
        Return a list of commands available to the specified actor.
        """


def make_command_list(obj):
    """
    Return a list of command classes provided by an object (ie: a module).
    :rtype: list
    """
    commands = []
    for name in obj.__dict__:
        c = getattr(obj, name)
        if (inspect.isclass(c) and issubclass(c, Command) and c != Command
                and not c.__dict__.get('abstract', False)):
            if not c in commands:
                commands.append(c)
    return commands


def all_commands(*objects):
    """
    Takes objects (including modules), and pulls out all command classes
    provided in their members and flattens them into a single command list.
    :rtype: list
    """
    commands = []
    for o in objects:
        if (inspect.isclass(o) and issubclass(o, Command)
                and not o.__dict__.get('abstract', False)):
            commands.append(o)
            continue
        for cmd in make_command_list(o):
            if not cmd in commands:
                commands.append(cmd)
    return commands
