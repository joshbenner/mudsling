from mudsling.commands import Command
from mudsling.parsers import MatchObject, StaticParser
from mudsling.objects import BaseObject
from mudsling.locks import Lock

from mudslingcore.scripting import ScriptableObject

match_scriptable = MatchObject(cls=ScriptableObject, show=True, context=False,
                               search_for='scriptable object')

can_script = Lock('has_perm(script anything) or can(script)')


class PropertyTypeStaticParser(StaticParser):
    types = {
        'str': str,
        'int': int,
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
    @add-property <obj>.<name>[=<type>]

    Add a property with the given type (string, integer, float, ObjRef).
    """
    aliases = ('@add-property', '@add-prop', '@property', '@prop')
    syntax = '<obj> {.} <propname> [{=} <datatype>]'
    arg_parsers = {
        'obj': match_scriptable,
        'datatype': PropertyTypeStaticParser
    }
    lock = can_script

    def run(self, actor, obj, propname, datatype):
        raise NotImplementedError()
