

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
        Returns the command set. Will cache the combiled command set for this
        object (and its ancestors, presumably), and use that cache unless the
        refresh parameter is True.

        @param refresh: If true, rebuilds command set cache for object.
        @return: set
        """
