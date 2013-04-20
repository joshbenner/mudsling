"""
Shared options for the twisted plugins. Since the custom app runner basically
passes the commandline arguments through, both proxy and server should both
parse the same arguments.
"""
import os
import sys

# Prefer libs we ship with.
basepath = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
libpath = os.path.join(basepath, "lib")
sys.path.insert(1, libpath)
del basepath, libpath

from twisted.python import usage


class Options(usage.Options):
    optFlags = [["debugger", "d", "Run in debugger-compatibility mode."]]
    optParameters = [
        ["gamedir", "g", "game", "The path to the game directory."]
    ]

    def configPaths(self):
        """
        Determine the list of locations where configuration files can be found.
        @rtype: list
        """
        return ["mudsling/defaults.cfg", "%s/settings.cfg" % self['gamedir']]
