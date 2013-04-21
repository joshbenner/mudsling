"""
Shared options for the twisted plugins. Since the custom app runner basically
passes the commandline arguments through, both proxy and server should both
parse the same arguments.
"""
import os
import sys

# Prefer libs we ship with. Put here because every process includes this early.
mudsling_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(1, os.path.join(mudsling_path, 'lib'))

from twisted.python import usage


class Options(usage.Options):
    optFlags = [["debugger", "d", "Run in debugger-compatibility mode."]]
    optParameters = [
        ["gamedir", "g", os.path.join(mudsling_path, "game"),
         "The path to the game directory."]
    ]

    def configPaths(self):
        """
        Determine the list of locations where configuration files can be found.
        @rtype: list
        """
        defaults = os.path.join(mudsling_path, 'src', 'defaults.cfg')
        return [defaults, "%s/settings.cfg" % self['gamedir']]


def get_options(args=None):
    """
    Parse the MUDSling commandline options from the argv after the script
    name.

    Upon failiure to parse, will print usage information and exit with code 1.

    @rtype: L{Options}
    """
    args = args or sys.argv[1:]
    options = Options()
    try:
        options.parseOptions(args)
    except usage.UsageError as e:
        sys.stderr.write(e.message + '\n' + str(options))
        exit(1)
    return options
