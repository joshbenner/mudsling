"""
Parsers are classes used to convert from strings representing a value to
the python value, and back again. The most straightforward case is converting
to/from input and a python value.
"""
from mudsling import registry
from mudsling.storage import StoredObject


class Parser(object):
    @classmethod
    def parse(cls, input):
        """
        Parse the input string into the value of the class.

        Upon failure, raise ValueError.

        @param input: The string to parse.
        @type input: C{str}
        """

    @classmethod
    def unparse(cls, val, obj=None):
        """
        Given a value, represent it as a string for consumption by a player.

        For simple objects, the default implementation may be sufficient.

        @param val: The value to represent as a string.
        @param obj: (optional) the object to be shown the string version.
        """
        return str(val)

#    @classmethod
#    def canParse(cls, input):
#        """
#        Determine if the raw input can be parsed into the value of this class.
#        Some implementations may call this before parsing, so descendants
#        should implement it even though parsing can raise exceptions.
#
#        @param input: The raw input to evaluate for parsability.
#        @returns: True if the input is parsable.
#        @rtype: C{bool}
#        """
#        return isinstance(input, basestring)


class IntParser(Parser):
    @classmethod
    def parse(cls, input):
        return int(input)


class FloatParser(Parser):
    @classmethod
    def parse(cls, input):
        return float(input)


class StringListParser(Parser):
    """
    Parses a comma-separated list into a list of strings.
    """
    delimiter = ','

    @classmethod
    def parse(cls, input):
        if isinstance(input, str) or isinstance(input, unicode):
            return map(str.strip, input.split(cls.delimiter))
        raise ValueError("Cannot parse list of strings from non-string.")

    @classmethod
    def unparse(cls, val, obj=None):
        return cls.delimiter.join(val)


class ObjClassParser(Parser):
    """
    Converts a MUDSling "pretty" class name to a game object class.
    """
    invalid_str = "INVALID_OBJCLASS"

    @classmethod
    def parse(cls, input):
        objClass = registry.classes.getClass(input)
        if objClass is None or not issubclass(objClass, StoredObject):
            raise ValueError("Invalid object class name: %r" % input)
        return objClass

    @classmethod
    def unparse(cls, val, obj=None):
        return registry.classes.getClassName(val) or cls.invalid_str


class BoolParser(Parser):
    """
    Parses various boolean representations into a C{bool} value.
    """
    trueVals = ('yes', 'true', '1', 'on')
    falseVals = ('no', 'false', '0', 'off')
    err = "Invalid true/false value: %r"

    @classmethod
    def parse(cls, input):
        m = input.strip().lower()
        if m in cls.trueVals:
            return True
        elif m in cls.falseVals:
            return False
        else:
            raise ValueError(cls.err % input)

    @classmethod
    def unparse(cls, val, obj=None):
        return cls.trueVals[0] if val else cls.falseVals[0]


class YesNoParser(BoolParser):
    trueVals = ('yes',)
    falseVals = ('no',)
    err = "Invalid yes/no value: %r"


class TrueFalseParser(BoolParser):
    trueVals = ('true',)
    falseVals = ('false',)


class OnOffParser(BoolParser):
    trueVals = ('on',)
    falseVals = ('off',)
    err = "Invalid on/off value: %r"
