import inspect

from mudsling import errors
from mudsling.storage import StoredObject, ObjRef
import mudsling.commands
import mudsling.match
import mudsling.errors
import mudsling.locks
import mudsling.objects
import mudsling.parsers

from mudsling.utils.sequence import CaselessDict

from mudslingcore.editor import EditorSession


def lock_can_configure(obj, who):
    """
    Lock function can_configure().

    True if user can configure settings on object.

    :type obj: ConfigurableObject
    """
    if obj.isa(ConfigurableObject):
        if who.has_perm('configure all objects'):
            return True
        elif (who.has_perm('configure own objects')
              and obj.isa(mudsling.objects.BaseObject)
              and obj.owner == who):
            return True
    return False


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

    # TODO: Refactor using mudsling.parsers?
    @staticmethod
    def parse_string_list(string):
        return map(str.strip, string.split(','))

    @staticmethod
    def parse_string_list_none_empty(string):
        return filter(lambda x: x, ObjSetting.parse_string_list(string))

    def display_value(self, obj):
        val = self.get_value(obj)
        if (inspect.isclass(self.parser)
                or isinstance(self.parser, mudsling.parsers.Parser)):
            return self.parser.unparse(val)
        else:
            return repr(val)

    def is_default(self, obj):
        """
        Determine if the setting is currently un-set for the obj, using the
        default.
        """
        attr = self.attr
        if attr is None:
            if 'unbound_settings' in obj.__dict__:
                return not self.name in obj.unbound_settings
            return True
        else:
            return not attr in obj.__dict__

    def set_value(self, obj, value):
        """
        Store the given value for this object setting. No validation or
        converstion.

        :raise errors.ObjSettingError: If setting the attribute results in
            an exception.

        :returns: True if storing the value was successful.
        :rtype: bool
        """
        attr = self.attr
        if attr is None:  # Store in unbound_settings
            if "unbound_settings" in obj.__dict__:
                if obj.unbound_settings is None:
                    obj.unbound_settings = CaselessDict()
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

    def set_value_from_input(self, obj, input):
        """
        Sets the value for the setting this instance describes on the provided
        object to the provided value.

        :returns: True if set action succeeds.
        :rtype: bool
        """
        try:
            if (inspect.isclass(self.parser)
                    or isinstance(self.parser, mudsling.parsers.Parser)):
                value = self.parser.parse(input)
            elif callable(self.parser):
                value = self.parser(obj, self, input)
            else:
                value = input
        except errors.ObjSettingError:
            raise
        except Exception as e:
            msg = "Error parsing input: %s" % e.message
            raise errors.ObjSettingError(obj, self.name, msg)

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
            if not issubclass(value, ObjRef) or not value.is_valid(self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)
        else:
            if not isinstance(value, self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)

        # If we get this far, then value is valid.
        return self.set_value(obj, value)

    def get_value(self, obj):
        attr = self.attr
        if attr is None:
            if "unbound_settings" in obj.__dict__:
                if self.name in obj.unbound_settings:
                    return obj.unbound_settings[self.name]
        else:
            if hasattr(obj, attr):
                return getattr(obj, attr)
        return self.default(obj) if callable(self.default) else self.default

    def reset_value(self, obj):
        attr = self.attr
        if (attr is None
                and "unbound_settings" in obj.__dict__
                and attr in obj.unbound_settings):
            del obj.unbound_settings[attr]
            return True
        elif attr in obj.__dict__:
            delattr(obj, attr)
            return True
        return False


class ConfigurableObject(mudsling.objects.BaseObject):
    """
    An object that has a configuration API.

    :cvar object_settings: Settings exposed by this class.
    :cvar _objSettings_cache: A cache of the class's settings after resolving
        all available settings through the MRO. See obj_settings.

    :ivar unbound_settings: A place to stash setting values that have no
        configured attribute for storage.
    """

    object_settings = [
        # Examples.
        # ObjSetting('name', str, 'name'),
        # ObjSetting('aliases', list, 'aliases', []
        #            ObjSetting.parse_string_list_none_empty)
    ]
    _objsettings_cache = None

    #: @type: dict
    unbound_settings = None

    @classmethod
    def obj_settings(cls):
        """
        Returns a dict of L{ObjSetting} instances that apply to this class. The
        ObjSettings come from this class and all ancestor classes that specify
        a list of ObjSettings.

        :return: Dict of ObjSetting instances describing the settings for obj.
        :rtype: dict of (str, ObjSetting)
        """
        if cls._objsettings_cache is not None:
            return cls._objsettings_cache
        mro = list(cls.__mro__)
        mro.reverse()
        settings = CaselessDict()
        for c in mro:
            if (issubclass(c, ConfigurableObject)
                    and 'object_settings' in c.__dict__):
                for spec in c.object_settings:
                    settings[spec.name] = spec
        cls._objsettings_cache = settings
        return settings

    def get_obj_setting(self, name):
        """
        Retrieve an object setting.

        :param name: The name of the object setting.
        :type name: str

        :rtype: ObjSetting
        """
        settings = self.obj_settings()
        if name not in settings:
            raise errors.SettingNotFound(self, name)
        return settings[name]

    def set_obj_setting(self, name, input):
        """
        Set the value of an object setting.
        :param name: The object setting to manipulate.
        :param input: The raw user input representing the value to store.
        """
        return self.get_obj_setting(name).set_value_from_input(self, input)

    def get_obj_setting_value(self, name):
        return self.get_obj_setting(name).get_value(self)

    def reset_obj_setting(self, name):
        return self.get_obj_setting(name).reset_value(self)

    def obj_setting_is_default(self, name):
        return self.get_obj_setting(name).is_default(self)


class SettingEditorSession(EditorSession):
    """
    An editor session that can modify an object setting.
    """
    __slots__ = ('setting_obj', 'setting_name')

    def __init__(self, owner, setting_obj, setting_name):
        """
        :param owner: The owner of the editor session.
        :type owner: EditorSessionHost

        :param setting_obj: The object where the setting is located.
        :type setting_obj: mudslingcore.objsettings.ConfigurableObject

        :param setting_name: The name of the setting to edit.
        :type setting_name: str
        """
        value = setting_obj.get_obj_setting_value(setting_name)
        super(SettingEditorSession, self).__init__(owner, preload=value)
        self.setting_obj = setting_obj
        self.setting_name = setting_name

    @property
    def session_key(self):
        return '%s:#%s.%s' % (self.__class__.__name__, self.setting_obj.obj_id,
                              self.setting_name)

    @property
    def description(self):
        objname = self.owner.name_for(self.setting_obj)
        return "'%s' setting on %s" % (self.setting_name, objname)
