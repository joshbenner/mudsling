from mudsling.commands import Command
from mudsling.parsers import MatchObject, StaticParser, StringTupleStaticParser
from mudsling.objects import BaseObject
from mudsling.locks import Lock

import mudslingcore.scripting as s
from mudslingcore.editor import EditorError

match_scriptable = MatchObject(cls=s.ScriptableObject, show=True, context=False,
                               search_for='scriptable object')

can_script = Lock('has_perm(script anything) or can(script)')


class PropertyTypeStaticParser(StaticParser):
    types = {
        'str': str,
        'string': str,
        'int': int,
        'number': int,
        'num': int,
        'float': float
    }

    @classmethod
    def parse(cls, input):
        input = input.lower()
        if input in cls.types:
            return cls.types[input]
        elif input == 'objref':
            return BaseObject

    @classmethod
    def unparse(cls, val, obj=None):
        for n, t in cls.types.iteritems():
            if val == t:
                return n
        if val == BaseObject:
            return 'ObjRef'
        return str(val)


class AddPropertyCmd(Command):
    """
    @add-property <obj>.<name> [with] type <type>

    Add a property with the given type (string, integer, float, ObjRef).
    """
    aliases = ('@add-property', '@add-prop', '@property', '@prop')
    syntax = '<obj> {.} <propname> [with] type <datatype>'
    arg_parsers = {
        'obj': match_scriptable,
        'datatype': PropertyTypeStaticParser
    }
    lock = can_script

    default_map = {
        str: '',
        int: 0,
        float: 0.0,
        BaseObject: None
    }

    def run(self, actor, obj, propname, datatype):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type propname: str
        :type datatype: type
        """
        prop = s.Property(propname.lower(), data_type=datatype,
                          value=self.default_map[datatype])
        try:
            obj.add_property(prop)
        except s.PropertyAlreadyDefined as e:
            raise self._err(e.message)
        else:
            typename = PropertyTypeStaticParser.unparse(prop.data_type)
            actor.tell('Created property: {m', obj, '{y.{c', prop.name, '{n ',
                       'with type "', typename, '".')


class RemPropertyCmd(Command):
    """
    @remve-property <obj>.<name>

    Remove a property from the object.
    """
    aliases = ('@remove-property', '@remove-prop', '@rem-property',
               '@rem-prop', '@rmprop', '@delete-property', '@delete-prop',
               '@del-property', '@del-prop')
    syntax = '<obj> {.} <propname>'
    arg_parsers = {'obj': match_scriptable}
    lock = can_script

    def run(self, actor, obj, propname):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type propname: str
        """
        try:
            prop = obj.remove_property(propname.lower())
        except s.PropertyNotFound as e:
            raise self._err(e.message)
        else:
            actor.tell('{yRemoved property {m', obj, '{y.{c', prop.name, '{y.')


class AddCommandCmd(Command):
    """
    @add-command <obj>:<name> [<syntax>]

    Add a scripted command to an object.
    """
    aliases = ('@add-command', '@add-cmd', '@addcmd', '@verb')
    syntax = '<obj> {:} <names> [<syntax>]'
    arg_parsers = {
        'obj': match_scriptable,
        'names': StringTupleStaticParser
    }
    lock = can_script

    def run(self, actor, obj, names, syntax):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type names: tuple of str
        :type syntax: str
        """
        names = tuple(n.lower() for n in names)
        command = s.ScriptedCommand(names, syntax=syntax or '')
        try:
            obj.add_scripted_command(command)
        except s.CommandAlreadyDefined as e:
            raise self._err(e.message)
        else:
            actor.tell('Added command: {m', obj, '{y:{g', command.name())


class RemoveCommandCmd(Command):
    """
    @remove-command <obj>:<command>

    Remove a scripted command from an object.
    """
    aliases = ('@remove-command', '@rem-command', '@remove-cmd', '@rem-cmd',
               '@rmcmd', '@rmverb')
    syntax = '<obj> {:} <name>'
    arg_parsers = {'obj': match_scriptable}
    lock = can_script

    def run(self, actor, obj, name):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type name: str
        """
        try:
            cmd = obj.remove_scripted_command(name.lower())
        except s.CommandNotFound as e:
            raise self._err(e.message)
        else:
            actor.tell('{rRemoved{n command: {m', obj, '{y:{g', cmd.name())


class ProgramCmd(Command):
    """
    @program <obj>:<command>

    Prompts for lines of code for the specified command.
    """
    aliases = ('@program', '@prog')
    syntax = '<obj> {:} <name>'
    arg_parsers = {'obj': match_scriptable}
    lock = can_script

    def run(self, actor, obj, name):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type name: str
        """
        try:
            cmd = obj.get_scripted_command(name)
        except s.CommandNotFound as e:
            raise self._err(e.message)
        else:
            actor.read_lines(self._program, args=(cmd,))

    def _program(self, lines, cmd):
        try:
            cmd.set_code('\n'.join(lines))
        except s.ScriptSyntaxError as e:
            raise self._err('Syntax error: {y%s' % e.message)
        else:
            self.actor.tell('Code set on ', self.parsed_args['obj'], ':',
                            cmd.name())


class EditCommandCmd(Command):
    """
    @edit-command <obj>:<command>

    Open script line editor to edit the command's script code.
    """
    aliases = ('@edit-command', '@edit-cmd')
    syntax = '<obj> {:} <name>'
    arg_parsers = {'obj': match_scriptable}
    lock = can_script

    def run(self, actor, obj, name):
        """
        :type actor: mudslingcore.objects.Player
        :type obj: ScriptableObject
        :type name: str
        """
        try:
            command = obj.get_scripted_command(name)
        except s.CommandNotFound as e:
            raise self._err(e.message)
        session = s.ScriptEditorSession(obj, name, actor, preload=command.code)
        try:
            actor.register_editor_session(session, activate=True)
        except EditorError as e:
            raise self._err(e.message)
        actor.tell('{gYou are now programming ', session.description, '.')
