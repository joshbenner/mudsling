"""
The app-wide configuration store for MUDSling. Any module can import this to
interact with the configuration.
"""
import ConfigParser
import inspect

from mudsling import utils
import mudsling.utils.modules
import mudsling.utils.time


class Config(ConfigParser.SafeConfigParser):
    """
    Custom config class that adds just a little sugar.
    """

    # Follow naming of other get*() functions.
    def getobject(self, section, option):
        """
        A convenience method which coerces the I{option} in the specified
        I{section} to an object loaded from the specified Python module path.
        """
        objPath = self.get(section, option)
        try:
            modPath, varName = objPath.rsplit('.', 1)  # Can throw ValueError.
            obj = utils.modules.variable_from_module(modPath, varName)
        except:
            raise ValueError("Invalid object path: %r", objPath)
        return obj

    def getclass(self, section, option):
        """
        A convenience method which coerces the I{option} in the specified
        I{section} to a class loaded from the specified Python module path.
        """
        obj = self.getobject(section, option)
        if inspect.isclass(obj):
            return obj
        else:
            raise TypeError("Invalid class: %r" % obj)

    def getinterval(self, section, option):
        """
        A convenience method which coerces the I{option} in the specified
        I{section} to an integer representing the number of seconds indicated
        by the value in a simple DHMS format.

        Examples: 5m30s, 2d12h

        @see: L{mudsling.utils.time.dhms_to_seconds}

        @rtype: C{int}
        """
        return utils.time.dhms_to_seconds(self.get(section, option))


config = Config()
