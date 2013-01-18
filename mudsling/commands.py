

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
