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

    def getdefault(self, section, option, raw=False, vars=None, default=None):
        if self.has_option(section, option):
            return self.get(section, option, raw=raw, vars=vars)
        else:
            return default

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

    # Modified to support blank section.
    def _read(self, fp, fpname):
        self._sections[''] = self._dict()
        cursect = self._sections['']          # None, or a dictionary
        optname = None
        lineno = 0
        e = None                              # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno += 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
                # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname].append(value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == ConfigParser.DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                        # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise ConfigParser.MissingSectionHeaderError(fpname,
                                                                 lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        optname = self.optionxform(optname.rstrip())
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos - 1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                            # allow empty values
                            if optval == '""':
                                optval = ''
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ConfigParser.ParsingError(fpname)
                        e.append(lineno, repr(line))
            # if any parsing errors occurred, raise an exception
        if e:
            raise e

        # join the multi-line values collected while reading
        all_sections = [self._defaults]
        all_sections.extend(self._sections.values())
        for options in all_sections:
            for name, val in options.items():
                if isinstance(val, list):
                    options[name] = '\n'.join(val)

    # Modified to support blank section.
    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        if section == ConfigParser.DEFAULTSECT:
            option = self.optionxform(option)
            return option in self._defaults
        elif section not in self._sections:
            return False
        else:
            option = self.optionxform(option)
            return (option in self._sections[section]
                    or option in self._defaults)

    # Modified to support blank section.
    def set(self, section, option, value=None):
        """Set an option.  Extend ConfigParser.set: check for string values."""
        if self._optcre is self.OPTCRE or value:
            if not isinstance(value, basestring):
                raise TypeError("option values must be strings")
        if value is not None:
            # check for bad percent signs:
            # first, replace all "good" interpolations
            tmp_value = value.replace('%%', '')
            tmp_value = self._interpvar_re.sub('', tmp_value)
            # then, check if there's a lone percent sign left
            if '%' in tmp_value:
                raise ValueError("invalid interpolation syntax in %r at "
                                 "position %d" % (value, tmp_value.find('%')))
        if section == ConfigParser.DEFAULTSECT:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise ConfigParser.NoSectionError(section)
        sectdict[self.optionxform(option)] = value

    # Modified to support blank section.
    def remove_option(self, section, option):
        """Remove an option."""
        if section == ConfigParser.DEFAULTSECT:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise ConfigParser.NoSectionError(section)
        option = self.optionxform(option)
        existed = option in sectdict
        if existed:
            del sectdict[option]
        return existed


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
