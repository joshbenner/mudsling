

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

    @cvar aliases: The strings that can match to trigger the command.
    @cvar args: The tuple of arg tokens used to determine if the parsed input
                matches the signature of this command.
    """

    aliases = ()
    args = (None, None, None)

    def matchParsedInput(self, input):
        """
        Determines if this command is a match for the ParsedInput provided. The
        generic version of this hook should be sufficient for most commands,
        but it can be overridden for extra magic.

        @param input: The ParsedInput to match against.
        @type input: mudsling.parse.ParsedInput

        @return: bool
        """
        dobjSpec, prepSpec, iobjSpec = self.args

    def matchPrepSpec(self, prepSpec, input):
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

    def matchObjSpec(self, objSpec, objStr):
        """
        Matches an arguments objSpec against the string that was parsed for its
        slot.

        @param objSpec: The spec to match against.
        @param objStr: The input string to match.

        @return: bool
        """
        if objSpec == 'any':
            return True

        if objSpec is None:
            return objStr == "" or objStr is None

        # objSpec can be a class
        #if isinstance(objSpec, type):


    def parseArgstr(self, argstr):
        """
        Here a command can perform any isolated parsing of the input it wishes.
        This hook is called before command execution.
        """

    def runCommand(self):
        """
        This is where the magic happens.
        """


class CommandProvider(object):
    """
    Objects that provide commands should have this class as a parent. Provides
    storage and methods for retrieving commands.

    @ivar commands: Contains set of commands provided by this object.
    @type commands: set
    """

    commands = set()

    def refresh_commands(self):
        """
        Rebuilds the instance's command set.
        """
        self.commands = self.build_command_set()

    def build_command_set(self):
        """
        Builds the command set. Children should override this, super, append
        their own commands to the set, and return the set.

        @return: set
        """
        return set()

    def get_commands(self, refresh=False):
        """
        Returns the command set. Will cache the compiled command set for this
        object (and its ancestors, presumably), and use that cache unless the
        refresh parameter is True.

        @param refresh: If true, rebuilds command set cache for object.
        @return: set
        """
