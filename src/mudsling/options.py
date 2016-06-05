"""
Shared options for the twisted plugins. Since the custom app runner basically
passes the commandline arguments through, both proxy and server should both
parse the same arguments.
"""
import os
import sys
from pkg_resources import resource_exists, resource_filename

from twisted.python import usage


class Options(usage.Options):
    optFlags = [["simple", "s", "Run in a single process with no proxy and a "
                                "simple Telnet service."]]
    optParameters = [
        ["gamedir", "g", os.path.abspath(os.path.curdir),
         "The path to the game directory."],
    ]

    def __init__(self):
        super(Options, self).__init__()
        self['extra_configs'] = []

    def config_paths(self):
        """
        Determine the list of locations where configuration files can be found.
        :rtype: list
        """
        paths = []
        if resource_exists('mudsling', 'defaults.cfg'):
            paths.append(resource_filename('mudsling', 'defaults.cfg'))
        paths.append("%s/settings.cfg" % self['gamedir'])
        paths.extend(self['extra_configs'])
        return [os.path.abspath(p) for p in paths]

    def opt_config(self, path):
        """
        Specify path to extra config file. Can be used more than once.
        """
        self['extra_configs'].append(os.path.abspath(path))

    opt_c = opt_config

    def opt_version(self):
        """
        Display MUDSling and Twisted versions, then exit.
        """
        import mudsling
        print "MUDSling version:", mudsling.version
        super(Options, self).opt_version()

    def postOptions(self):
        self['gamedir'] = os.path.abspath(self['gamedir'])


def get_options(args=None):
    """
    Parse the MUDSling commandline options from the argv after the script
    name.

    Upon failiure to parse, will print usage information and exit with code 1.

    :rtype: Options
    """
    args = sys.argv[1:] if args is None else args
    options = Options()
    try:
        options.parseOptions(args)
    except usage.UsageError as e:
        sys.stderr.write(e.message + '\n' + str(options))
        exit(1)
    return options
