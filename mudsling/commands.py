import re

import inflect

from mudsling.utils import string


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

    @cvar aliases: Regular expressions that can match to trigger the command.
    @cvar args: The tuple of arg tokens used to determine if the parsed input
        matches the signature of this command.
    @cvar required_perm: An object must have this perm to use this command.

    @ivar obj: The object hosting this command.
    @ivar input: The ParsedInput which led to this command being executed.
    @ivar actor: The object responsible for the input leading to execution.
    @ivar game: Handy reference to the game object.
    """

    aliases = ()
    _compiled_aliases = []
    args = (None, None, None)
    required_perm = None

    #: @type: mudsling.objects.BaseObject
    obj = None

    #: @type: mudsling.objects.BaseObject
    actor = None

    #: @type: mudsling.parse.ParsedInput
    input = None

    #: @type: mudsling.core.MUDSling
    game = None

    @classmethod
    def checkAccess(cls, hostObj, actor):
        """
        Determine if an object is allowed to use this command.

        @param hostObj: The object providing this command.
        @type hostObj: mudsling.objects.BaseObject

        @param actor: The object that wants to use this command.
        @type actor: mudsling.objects.BaseObject

        @rtype: bool
        """
        if cls.required_perm is not None:
            return actor.hasPerm(cls.required_perm)
        return True

    @classmethod
    def matchInput(cls, hostObj, input):
        """
        Determines if this command is a match for the ParsedInput provided. The
        generic version of this hook should be sufficient for most commands,
        but it can be overridden for extra magic.

        @param hostObj: The object hosting the command for this check.
        @type hostObj: mudsling.objects.BaseObject

        @param input: The ParsedInput to match against.
        @type input: mudsling.parse.ParsedInput

        @rtype: bool
        """
        if len(cls.aliases) > len(cls._compiled_aliases):
            cls.compileAliases()

        cmdstr = input.cmdstr
        match = False
        for alias in cls._compiled_aliases:
            if alias.match(cmdstr):
                match = True

        if not match:
            return False

        dobjSpec, prepSpec, iobjSpec = cls.args
        i = input
        prepMatch = cls.matchPrepSpec(prepSpec, input)
        dobjMatch = cls.matchObjSpec(hostObj, dobjSpec, i.dobjstr, i.dobj)
        iobjMatch = cls.matchObjSpec(hostObj, iobjSpec, i.iobjstr, i.iobj)

        return prepMatch and dobjMatch and iobjMatch

    @classmethod
    def compileAliases(cls):
        """
        Compile alias regexes for speedy reuse.
        """
        compiled = []
        for alias in cls.aliases:
            compiled.append(re.compile(alias, re.IGNORECASE))
        cls._compiled_aliases = compiled

    @classmethod
    def matchPrepSpec(cls, prepSpec, input):
        """
        Check if the preposition spec matches the ParsedInput.

        @param prepSpec: The prepSpec to compare against.
        @type prepSpec: str or None

        @param input: The ParsedInput to compare.
        @type input: mudsling.parse.ParsedInput

        @rtype: bool
        """
        if prepSpec is None:
            return input.prep is None

        if prepSpec == 'any' and input.prep is not None:
            return True

        # Check for optional preposition
        if prepSpec.startswith('?'):
            if input.prep:
                # Prep is optional, but provided: make sure it matches.
                return prepSpec[1:] in input.prep
            # Prep is optional and not provided: that's a pass.
            return True

        # prepSpec is neither 'any' nor None, so it must be a string specifying
        # the preoposition it wants. If the prepSpec is in the preposition set
        # in the input, then we have a match.
        return prepSpec in (input.prep or ())

    @classmethod
    def matchObjSpec(cls, hostObj, objSpec, string, obj):
        """
        Determines if the input string and/or matched object for an object slot
        matches the arg spec.

        @param hostObj: The object that is hosting this command for this check.
        @param objSpec: The spec to match against.
        @param string: The input string to match.
        @param obj: The object match by the command parser.

        @rtype: bool
        """
        if objSpec == 'any':
            return True

        if objSpec is None:
            return string == "" or string is None

        if objSpec == 'this' or objSpec == 'self':
            return obj == hostObj

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

    def __init__(self, game, obj=None, input=None, actor=None):
        """
        @param game: Reference to the game instance.
        @type game: mudsling.server.MUDSling

        @param obj: The object hosting the command.
        @type obj: mudsling.objects.BaseObject

        @param input: The ParsedInput that lead to this command instance.
        @type input: mudsling.parse.ParsedInput

        @param actor: The object executing this command.
        @type actor: mudsling.objects.BaseObject
        """
        self.game = game
        self.obj = obj
        self.input = input
        self.actor = actor

    def execute(self):
        """
        Execution entry point for the command. The object system should call
        this once it has decided to run the command.
        """
        if self.prepare():
            self.run(self.obj, self.input, self.actor)

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

    def run(self, this, input, actor):
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

#class CommandProvider(object):
#    """
#    Objects that provide commands should have this class as a parent. Provides
#    storage and methods for retrieving commands.
#
#    @ivar commands: Contains set of commands provided by this object.
#    @type commands: set
#    """
#
#    commands = set()
#
#    def refresh_commands(self):
#        """
#        Rebuilds the instance's command set.
#        """
#        self.commands = self.build_command_set()
#
#    def build_command_set(self):
#        """
#        Builds the command set. Children should override this, super, append
#        their own commands to the set, and return the set.
#
#        @return: set
#        """
#        return set()
#
#    def get_commands(self, refresh=False):
#        """
#        Returns the command set. Will cache the compiled command set for this
#        object (and its ancestors, presumably), and use that cache unless the
#        refresh parameter is True.
#
#        @param refresh: If true, rebuilds command set cache for object.
#        @return: set
#        """
