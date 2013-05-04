"""
The app-wide configuration store for MUDSling. Any module can import this to
interact with the configuration.
"""
import ConfigParser
import inspect

from mudsling import utils
import mudsling.utils.modules


class Config(ConfigParser.SafeConfigParser):
    """
    Custom config class that adds just a little sugar.
    """
    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False,
                       'enabled': True, 'disabled': False}

    def __init__(self, *args, **kwargs):
        ConfigParser.SafeConfigParser.__init__(self, *args, **kwargs)
        self._configSections = {}

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
        import mudsling.utils.time  # Avoid circular import at module-level.
        return utils.time.dhms_to_seconds(self.get(section, option))

    def section(self, section):
        if section not in self._configSections:
            if self.has_section(section):
                self._configSections[section] = ConfigSection(self, section)
            else:
                raise ConfigParser.NoSectionError(section)
        return self._configSections[section]

    def __getitem__(self, item):
        return self.section(item)


class ConfigSection(object):
    """
    Encapsulates a section of configuration within a ConfigParser.
    """
    def __init__(self, configParser, section):
        """
        @param configParser: The ConfigParser instance upon which to base this
            config section.
        @param section: The config section to bind to.
        """
        self.config = configParser
        self.section = section

    def __getitem__(self, item):
        return self.get(item)

    def __iter__(self):
        for item in self.items():
            yield item

    # Yes, there are ways to do this that would be more succinct. However, this
    # is explicit, readable, obvious, and very compatible with IDE completion.

    def get(self, option, raw=False, vars=None):
        return self.config.get(self.section, option, raw, vars)

    def getint(self, option):
        return self.config.getint(self.section, option)

    def getfloat(self, option):
        return self.config.getfloat(self.section, option)

    def getboolean(self, option):
        return self.config.getboolean(self.section, option)

    def getobject(self, option):
        return self.config.getobject(self.section, option)

    def getclass(self, option):
        return self.config.getclass(self.section, option)

    def getinterval(self, option):
        return self.config.getinterval(self.section, option)

    def items(self, raw=False, vars=None):
        return self.config.items(self.section, raw, vars)

    def set(self, option, value):
        return self.config.set(self.section, option, value)

    def remove_option(self, option):
        return self.config.remove_option(self.section, option)

    def has_option(self, option):
        return self.config.has_option(self.section, option)

    def options(self):
        return self.config.options(self.section)


config = Config()
