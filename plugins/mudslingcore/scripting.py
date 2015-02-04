import logging
import types

import lupa
from lupa import LuaRuntime

from mudsling.objects import Object
from mudsling.commands import Command, SyntaxParseError, Syntax
from mudsling.storage import PersistentSlots, Persistent
from mudsling.errors import Error

from mudslingcore.objsettings import ObjSetting, ConfigurableObject


class PropertyAlreadyDefined(Error):
    pass


class PropertyNotFound(Error):
    pass


class CommandAlreadyDefined(Error):
    pass


class CommandNotFound(Error):
    pass


def filter_attribute_access(obj, attr_name, is_setting):
    if ((not isinstance(attr_name, basestring)) or attr_name.startswith('__')
        or (isinstance(obj, (types.FunctionType, types.MethodType))
            and attr_name.startswith('func_'))):
        raise AttributeError('access denied to %r.%s' % (obj, attr_name))
    return attr_name


try:
    lua = lupa.LuaRuntime(attribute_filter=filter_attribute_access)
    lua_version = lua.eval('_VERSION')
except:
    lua_version = '?'
if lua_version != 'Lua 5.2':
    logging.error('Incorrect Lua version: %s', lua_version)
    lua_enabled = False
else:
    lua_enabled = True

SANDBOX_SCRIPT = r'''
function sandbox_run(untrusted_code, extra_env)
    extra_env = extra_env or {}
    local env = {
        ipairs = ipairs,
        next = next,
        pairs = pairs,
        pcall = pcall,
        tonumber = tonumber,
        tostring = tostring,
        type = type,
        unpack = unpack,
        coroutine = { create = coroutine.create, resume = coroutine.resume,
            running = coroutine.running, status = coroutine.status,
            wrap = coroutine.wrap },
        string = { byte = string.byte, char = string.char, find = string.find,
            format = string.format, gmatch = string.gmatch, gsub = string.gsub,
            len = string.len, lower = string.lower, match = string.match,
            rep = string.rep, reverse = string.reverse, sub = string.sub,
            upper = string.upper },
        table = { insert = table.insert, maxn = table.maxn,
            remove = table.remove, sort = table.sort },
        math = { abs = math.abs, acos = math.acos, asin = math.asin,
            atan = math.atan, atan2 = math.atan2, ceil = math.ceil,
            cos = math.cos, cosh = math.cosh, deg = math.deg, exp = math.exp,
            floor = math.floor, fmod = math.fmod, frexp = math.frexp,
            huge = math.huge, ldexp = math.ldexp, log = math.log,
            log10 = math.log10, max = math.max, min = math.min,
            modf = math.modf, pi = math.pi, pow = math.pow, rad = math.rad,
            random = math.random, sin = math.sin, sinh = math.sinh,
            sqrt = math.sqrt, tan = math.tan, tanh = math.tanh },
        os = { clock = os.clock, difftime = os.difftime, time = os.time },
    }
    for k, v in pairs(extra_env) do env[k] = v end
    local untrusted_function, message = load(untrusted_code, nil, 't', env)
    if not untrusted_function then return nil, message end
    return pcall(untrusted_function)
end
'''
lua.execute(SANDBOX_SCRIPT)
_sandbox_run = lua.globals().sandbox_run


def sandbox_run(code, env=None):
    """
    Run untrusted Lua code.

    :param code: The code to execute.
    :type code: str

    :return: The result of attempting execution: (success, error or *return)
    :rtype: tuple
    """
    env = env or {}
    r = _sandbox_run(code, lua.table_from(env))
    if isinstance(r, bool):
        r = (r,)
    if r[0] is None:
        r = list(r)
        r[0] = False
        r = tuple(r)
    return r


class ScriptedCommand(Persistent):
    """
    Scripted command.

    This class mimics a Command subclass for the purposes of command
    matching and execution.
    """
    _transient_vars = ('_compiled_syntax',)

    def __init__(self, aliases, syntax='', code=None):
        if isinstance(aliases, basestring):
            aliases = (str(aliases),)
        self.aliases = tuple(aliases)
        self.syntax = syntax
        if code is not None:
            self.set_code(code)
        else:
            self.code = None

    @property
    def key(self):
        try:
            return self.aliases[0]
        except IndexError:
            raise Exception('Invalid command key')

    def set_code(self, code):
        self.code = code

    @property
    def compiled_syntax(self):
        try:
            return self._compiled_syntax
        except AttributeError:
            self._compile_syntax()
        return self._compiled_syntax

    def name(self):
        """
        Mimics :method:`mudsling.commands.Command.name`.
        """
        return self.aliases[0] if len(self.aliases) else 'ERROR NO CMD ALIAS'

    def _compile_syntax(self):
        """
        Mimics :method:`mudsling.commands.Command._compile_syntax`.
        """
        try:
            self._compiled_syntax = Syntax(self.syntax)
        except SyntaxParseError as e:
            logging.error("Cannot parse %s syntax: %s"
                          % (self.name(), e.message))
            return False

    def matches(self, cmdstr):
        """
        Mimics :method:`mudsling.commands.Command.matches`.
        """
        return cmdstr.split('/')[0] in self.aliases

    def check_access(self, host, actor):
        """
        Mimics :method:`mudsling.commands.Command.check_access`.
        """
        return True

    def __call__(self, *args, **kwargs):
        """
        Mimics :method:`mudsling.commands.Command.__init__`.
        """
        return ScriptCommandRunner(self, *args, **kwargs)

    def run(self, this, actor, args):
        sandbox_run(self.code, env={
            'this': this,
            'actor': actor,
            'args': args,
            'here': this.location
        })


class ScriptCommandRunner(Command):
    """
    A command class that executes scripted commands. It is instantiated when a
    :class:`ScriptedCommand` instance is called.
    """

    # This prevents match_syntax from compiling.
    _syntax = None

    def __init__(self, script, *args, **kwargs):
        """
        :param script: The ScriptedCommand spawning this instance.
        :type script: ScriptedCommand
        """
        super(ScriptCommandRunner, self).__init__(*args, **kwargs)
        self.script = script
        self._syntax = (script.compiled_syntax,)
        if '<this>' in script.syntax.lower():
            self.arg_parsers = {'this': 'THIS'}

    @property
    def syntax(self):
        return self.script.syntax

    @property
    def aliases(self):
        return self.script.aliases

    def name(self):
        return self.script.name()

    def syntax_help(self):
        return '{ySyntax: {c%s %s' % (self.name(), self.syntax)

    def run(self, this, actor, args):
        if not lua_enabled:
            logging.warn('Lua disabled, blocking command %s', self.name())
            raise self._err('Internal Error.')
        self.script.run(this, actor, args)


class PropertyObjSetting(ObjSetting):
    def __init__(self, prop, parser=None):
        self.property = prop
        super(PropertyObjSetting, self).__init__(prop.name, type=prop.data_type,
                                                 parser=parser)

    def set_value(self, obj, value):
        self.property.value = value
        return True

    def get_value(self, obj):
        return self.property.value


class Property(PersistentSlots):
    """
    Represents object-specific setting.
    """
    __slots__ = ('name', 'data_type', 'value', '_obj_setting')
    _transient_vars = ('_obj_setting',)

    def __init__(self, name, data_type=str, value=None):
        self.name = name
        self.data_type = data_type
        self.value = value

    @property
    def obj_setting(self):
        try:
            return self._obj_setting
        except AttributeError:
            self._obj_setting = self.generate_obj_setting()
        return self._obj_setting

    def generate_obj_setting(self):
        return PropertyObjSetting(self)


class ScriptableObject(Object, ConfigurableObject):
    """
    An object which can have a script that defines additional ObjSetting
    instances and additional commands that are unique to this object.
    """
    _transient_vars = ('_property_collection', '_property_objsetting_cache')

    #: :type: dict of (str, )
    _properties = {}

    #: :type: PropertyCollection
    _property_collection = None

    _property_objsetting_cache = None

    #: :type: list of ScriptedCommand
    scripted_commands = []

    def obj_settings(self):
        if self._property_objsetting_cache is None:
            # noinspection PyArgumentList
            settings = dict(super(ScriptableObject, self).obj_settings())
            settings.update({p.name: p.obj_setting
                             for p in self._properties.itervalues()})
            self._property_objsetting_cache = settings
        return self._property_objsetting_cache

    def _clear_property_objsetting_cache(self):
        self._property_objsetting_cache = None

    def add_property(self, prop):
        """
        :type prop: Property
        """
        if '_properties' not in self.__dict__:
            self._properties = {}
        if prop.name in self.obj_settings():
            raise PropertyAlreadyDefined('Property or setting %s already exists'
                                         % prop.name)
        self._properties[prop.name] = prop
        self._clear_property_objsetting_cache()

    def remove_property(self, name):
        if name in self._properties:
            self.reset_obj_setting(name)
            prop = self._properties[name]
            del self._properties[name]
            self._clear_property_objsetting_cache()
            return prop
        else:
            raise PropertyNotFound("Property %s does not exist" % name)

    def has_property(self, name):
        return name in self._properties

    @property
    def properties(self):
        if '_property_collection' not in self.__dict__:
            self._property_collection = PropertyCollection(self.ref())
        return self._property_collection

    def add_scripted_command(self, command):
        name = command.name()
        for cmd in self.scripted_commands:
            if name in cmd.aliases:
                msg = '%r already defines a "%s" command' % (self, name)
                raise CommandAlreadyDefined(msg)
        if 'scripted_commands' not in self.__dict__:
            self.scripted_commands = []
        self.scripted_commands.append(command)

    def remove_scripted_command(self, name):
        for i, cmd in enumerate(list(self.scripted_commands)):
            if cmd.name() == name:
                del self.scripted_commands[i]
                return cmd
        raise CommandNotFound('%r does not define command "%s"' % (self, name))

    def get_scripted_command(self, name):
        name = name.lower()
        for cmd in self.scripted_commands:
            if name in cmd.aliases:
                return cmd
        raise CommandNotFound('%r does not define command "%s"' % (self, name))

    def commands_for(self, actor):
        commands = super(ScriptableObject, self).commands_for(actor)
        commands.add_commands(self.scripted_commands)
        return commands


class PropertyCollection(object):
    __slots__ = ('__host',)

    def __init__(self, host):
        """
        :type host: ScriptableObject
        """
        self.__host = host

    def __getattr__(self, name):
        if self.__host.has_property(name):
            return self.__host.get_obj_setting_value(name)
        else:
            raise PropertyNotFound('%r has no %s property'
                                   % (self.__host, name))

    def __setattr__(self, name, value):
        if name == '_PropertyCollection__host':
            super(PropertyCollection, self).__setattr__(name, value)
        elif self.__host.has_property(name):
            self.__host.set_obj_setting(name, value)
        else:
            raise PropertyNotFound('%r has no %s property'
                                   % (self.__host, name))
