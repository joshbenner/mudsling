from mudsling.commands import Command
from mudsling.parsers import MatchObject, StaticParser
from mudsling.objects import BaseObject
from mudsling.locks import Lock

import mudslingcore.scripting as s

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
