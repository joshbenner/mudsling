"""
Parsers are classes used to convert from strings representing a value to
the python value, and back again. The most straightforward case is converting
to/from input and a python value.
"""
from mudsling import registry
from mudsling import errors
from mudsling import match
from mudsling.storage import StoredObject


class StaticParser(object):
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


class IntStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        return int(input)


class FloatStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        return float(input)


class StringListStaticParser(StaticParser):
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


class ObjClassStaticParser(StaticParser):
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


class BoolStaticParser(StaticParser):
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


class YesNoStaticParser(BoolStaticParser):
    trueVals = ('yes',)
    falseVals = ('no',)
    err = "Invalid yes/no value: %r"


class TrueFalseStaticParser(BoolStaticParser):
    trueVals = ('true',)
    falseVals = ('false',)


class OnOffStaticParser(BoolStaticParser):
    trueVals = ('on',)
    falseVals = ('off',)
    err = "Invalid on/off value: %r"


class Parser(object):
    """
    A parser class that has configuration and therefore is instanced.
    """
    def parse(self, input, obj=None):
        """
        Parse the input and return the value. Can raise errors.

        @param input: The user input to parse.
        @param obj: If parsing from an object's perspective, the object.
        """


class MatchObject(Parser):
    """
    Parser to match an object from the perspective of another object.
    """
    def __init__(self, cls=StoredObject, err=True, searchFor=None, show=False):
        """
        @param cls: Matching object must be of this objClass.
        @param err: If True, raises a L{mudsling.errors.MatchError}.
        @param searchFor: String describing what is being sought.
        @param show: If true, includes list of objects for ambiguous matches.
        """
        self.objClass = cls
        self.err = err
        self.searchFor = searchFor
        self.show = show

    def parse(self, input, obj=None):
        if obj is None:
            return False
        m = obj.matchObject(input, cls=self.objClass, err=False)
        if len(m) == 1:
            return m[0]
        else:
            msg = match.match_failed(
                matches=m,
                search=input,
                searchFor=self.searchFor,
                show=self.show
            )
            err = errors.AmbiguousMatch(msg) if m else errors.FailedMatch(msg)
            if self.err:
                raise err
            else:
                return err
