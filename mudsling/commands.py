import re

# Prepositions used in parsing input.
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

    @ivar obj: The object hosting this command.
    @ivar input: The ParsedInput which led to this command being executed.
    @ivar actor: The object responsible for the input leading to execution.
    """

    aliases = ()
    _compiled_aliases = []
    args = (None, None, None)

    #: @type: mudsling.objects.BaseObject
    obj = None

    #: @type: mudsling.objects.BaseObject
    actor = None

    #: @type: mudsling.parsed.ParsedInput
    input = None

    @classmethod
    def matchParsedInput(cls, hostObj, input):
        """
        Determines if this command is a match for the ParsedInput provided. The
        generic version of this hook should be sufficient for most commands,
        but it can be overridden for extra magic.

        @param hostObj: The object hosting the command for this check.
        @param input: The ParsedInput to match against.
        @type input: mudsling.parse.ParsedInput

        @return: bool
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
        return (cls.matchPrepSpec(prepSpec, input)
                and cls.matchObjSpec(hostObj, dobjSpec, i.dobjstr, i.dobj)
                and cls.matchObjSpec(hostObj, iobjSpec, i.iobjstr, i.iobj))

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
        @param input: The ParsedInput to compare.
        @type input: mudsling.parse.ParsedInput

        @return: bool
        """
        if prepSpec == 'any' and input.prep is not None:
            return True

        if prepSpec is None:
            return input.prep is None

        # prepSpec is neither 'any' nor None, so it must be a string specifying
        # the preoposition it wants. If the prepSpec is in the preposition set
        # in the input, then we have a match.
        return prepSpec in input.prep

    @classmethod
    def matchObjSpec(cls, hostObj, objSpec, string, obj):
        """
        Determines if the input string and/or matched object for an object slot
        matches the arg spec.

        @param hostObj: The object that is hosting this command for this check.
        @param objSpec: The spec to match against.
        @param string: The input string to match.
        @param obj: The object match by the command parser.

        @return: bool
        """
        if objSpec == 'any':
            return True

        if objSpec is None:
            return string == "" or string is None

        if objSpec == 'this' or objSpec == 'self':
            return obj == hostObj

        return False

    def __init__(self, obj=None, input=None, actor=None):
        self.obj = obj
        self.input = input
        self.actor = actor

    def execute(self):
        """
        Execution entry point for the command. The object system should call
        this once it has decided to run the command.
        """
        self.prepare()
        self.run()

    def prepare(self):
        """
        Here a command can perform any isolated parsing of the input or other
        preparation it wishes. This hook is called before command execution.

        This is a handy place to do any complex (and possibly re-usable)
        custom parsing of the command input.
        """

    def run(self):
        """
        This is where the magic happens.
        """


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
