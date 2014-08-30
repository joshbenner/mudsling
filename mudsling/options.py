"""
Shared options for the twisted plugins. Since the custom app runner basically
passes the commandline arguments through, both proxy and server should both
parse the same arguments.
"""
import os
import sys

mudsling_path = os.path.dirname(os.path.dirname(__file__))

from twisted.python import usage


class Options(usage.Options):
    optFlags = [["simple", "s", "Run in a single process with no proxy and a "
                                "simple Telnet service."]]
    optParameters = [
        ["gamedir", "g", os.path.join(mudsling_path, "game"),
         "The path to the game directory."],
        ["config", "c", None, "Specify path to extra configuration file."],
    ]

    def __init__(self):
        super(Options, self).__init__()
        self['extra_plugin_paths'] = []

    def configPaths(self):
        """
        Determine the list of locations where configuration files can be found.
        :rtype: list
        """
        defaults = os.path.join(mudsling_path, 'defaults.cfg')
        paths = [defaults, "%s/settings.cfg" % self['gamedir']]
        if self['config'] is not None:
            paths.append(self['config'])
        return paths

    def pluginPaths(self):
        paths = [os.path.join(mudsling_path, 'plugins'),
                 os.path.join(self['gamedir'], 'plugins')]
        paths.extend(self['extra_plugin_paths'])
        return paths

    def opt_plugins(self, path):
        """
        Specify the path to a directory containing additional plugin packages.
        The 'plugin' directory in the game directory is searched automatically.
        This option may be used multiple times.
        """
        self['extra_plugin_paths'].append(os.path.abspath(path))

    opt_p = opt_plugins

    def opt_version(self):
        """
        Display MUDSling and Twisted versions, then exit.
        """
        import mudsling
        print "MUDSling version:", mudsling.version
        super(Options, self).opt_version()


def get_options(args=None):
    """
    Parse the MUDSling commandline options from the argv after the script
    name.

    Upon failiure to parse, will print usage information and exit with code 1.

    :rtype: Options
    """
    args = args or sys.argv[1:]
    options = Options()
    try:
        options.parseOptions(args)
    except usage.UsageError as e:
        sys.stderr.write(e.message + '\n' + str(options))
        exit(1)
    return options
