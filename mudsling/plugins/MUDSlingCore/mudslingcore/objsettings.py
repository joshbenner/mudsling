import inspect

from mudsling import errors
from mudsling.storage import StoredObject, ObjRef, Persistent


class ObjSetting(object):
    """
    Describes an object setting available in-game.
    """

    name = ''
    type = None
    attr = None
    parser = None
    validator = None
    default = None

    def __init__(self, name, type=str, attr=None, default=None, parser=None,
                 validator=None):
        self.name = name
        self.type = type
        self.attr = attr
        self.parser = parser
        self.validator = validator
        self.default = default

    @staticmethod
    def parseStringList(string):
        return map(str.strip, string.split(','))

    @staticmethod
    def parseStringListNoneEmpty(string):
        return filter(lambda x: x, ObjSetting.parseStringList(string))

    def setValue(self, obj, value):
        """
        Store the given value for this object setting. No validation or
        converstion.

        @raise L{errors.ObjSettingError}: If setting the attribute results in
            an exception.

        @returns: True if storing the value was successful.
        @rtype: C{bool}
        """
        attr = self.attr
        if attr is None:  # Store in unbound_settings
            if "unbound_settings" in obj.__dict__:
                if obj.unbound_settings is None:
                    obj.unbound_settings = {}
                obj.unbound_settings[self.name] = value
                return True
            else:
                return False
        else:
            if hasattr(obj, attr):
                try:
                    setattr(obj, attr, value)
                    return True
                except Exception as e:
                    raise errors.ObjSettingError(obj, self.name, e.message)
            else:
                return False

    def setValueFromInput(self, obj, input):
        """
        Sets the value for the setting this instance describes on the provided
        object to the provided value.

        @returns: True if set action succeeds.
        @rtype: C{bool}
        """
        if callable(self.parser):
            try:
                if inspect.isclass(self.parser):
                    value = self.parser.parse(input)
                else:
                    value = self.parser(obj, self, input)
            except errors.ObjSettingError:
                raise
            except Exception as e:
                msg = "Error parsing input: %s" % e.message
                raise errors.ObjSettingError(obj, self.name, msg)
        else:
            value = input

        if callable(self.validator):
            try:
                valid = self.validator(obj, self, value)
            except Exception as e:
                raise errors.ObjSettingError(obj, self.name, e.message)
            if not valid:
                raise errors.InvalidSettingValue(obj, self.name, value)

        # Type validation for StoredObject is a little different since we use
        # ObjRef in most cases instead of direct references.
        if issubclass(self.type, StoredObject):
            if not issubclass(value, ObjRef) or not value.isValid(self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)
        else:
            if not isinstance(value, self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)

        # If we get this far, then value is valid.
        return self.setValue(obj, value)

    def getValue(self, obj):
        attr = self.attr
        if attr is None:
            if "unbound_settings" in obj.__dict__:
                if attr in obj.unbound_settings:
                    return obj.unbound_settings[attr]
        else:
            if hasattr(obj, attr):
                return getattr(obj, attr)
        return self.default


class ConfigurableObject(Persistent):
    """
    An object that has a configuration API.

    @cvar object_settings: Settings exposed by this class.
    @cvar _objSettings_cache: A cache of the class's settings after resolving
        all available settings through the MRO. See L{objSettings}.

    @ivar unbound_settings: A place to stash setting values that have no
        configured attribute for storage.
    """

    object_settings = [
        # Examples.
        # ObjSetting('name', str, 'name'),
        # ObjSetting('aliases', list, 'aliases',
        #            ObjSetting.parseStringListNoneEmpty)
    ]
    _objSettings_cache = None

    #: @type: dict
    unbound_settings = None

    @classmethod
    def objSettings(cls):
        """
        Returns a dict of L{ObjSetting} instances that apply to this class. The
        ObjSettings come from this class and all ancestor classes that specify
        a list of ObjSettings.

        @return: Dict of ObjSetting instances describing the settings for obj.
        @rtype: C{dict} of C{str}:L{ObjSetting}
        """
        if cls._objSettings_cache is not None:
            return cls._objSettings_cache
        mro = list(cls.__mro__)
        mro.reverse()
        settings = {}
        for c in mro:
            if (issubclass(c, ConfigurableObject)
                    and 'object_settings' in c.__dict__):
                for spec in c.object_settings:
                    settings[spec.name] = spec
        cls._objSettings_cache = settings
        return settings

    def setObjSetting(self, name, input):
        """
        Set the value of an object setting.
        @param name: The object setting to manipulate.
        @param input: The raw user input representing the value to store.
        """
        settings = self.objSettings()
        if name not in settings:
            raise errors.SettingNotFound(self, name)
        return settings[name].setValue(self, input)

    def getObjSetting(self, name):
        settings = self.objSettings()
        if name not in settings:
            raise errors.SettingNotFound(self, name)
        return settings[name].getValue(self)
