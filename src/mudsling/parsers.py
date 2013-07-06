"""
Parsers are classes used to convert from strings representing a value to
the python value, and back again. The most straightforward case is converting
to/from input and a python value.
"""
from mudsling import registry
from mudsling import errors
from mudsling import match
from mudsling.storage import StoredObject

from mudsling import utils
import mudsling.utils.time
import mudsling.utils.units


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
        raise errors.ParseError("Cannot parse strings from non-string.")

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
        objClass = registry.classes.get_class(input)
        if objClass is None or not issubclass(objClass, StoredObject):
            raise errors.ParseError("Invalid object class name: %r" % input)
        return objClass

    @classmethod
    def unparse(cls, val, obj=None):
        return registry.classes.get_class_name(val) or cls.invalid_str


class BoolStaticParser(StaticParser):
    """
    Parses various boolean representations into a C{bool} value.
    """
    true_vals = ('yes', 'true', '1', 'on')
    false_vals = ('no', 'false', '0', 'off')
    err = "Invalid true/false value: %r"

    @classmethod
    def parse(cls, input):
        m = input.strip().lower()
        if m in cls.true_vals:
            return True
        elif m in cls.false_vals:
            return False
        else:
            raise errors.ParseError(cls.err % input)

    @classmethod
    def unparse(cls, val, obj=None):
        return cls.true_vals[0] if val else cls.false_vals[0]


class YesNoStaticParser(BoolStaticParser):
    true_vals = ('yes',)
    false_vals = ('no',)
    err = "Invalid yes/no value: %r"


class TrueFalseStaticParser(BoolStaticParser):
    true_vals = ('true',)
    false_vals = ('false',)


class OnOffStaticParser(BoolStaticParser):
    true_vals = ('on',)
    false_vals = ('off',)
    err = "Invalid on/off value: %r"


class DhmsStaticParser(StaticParser):
    """
    @see L{mudsling.utils.time.dhms_to_seconds}
    """
    @classmethod
    def parse(cls, input):
        try:
            return utils.time.dhms_to_seconds(input)
        except ValueError:
            raise errors.ParseError("Invalid DHMS value. Example: 1d5h30m")

    @classmethod
    def unparse(cls, val, obj=None):
        return utils.time.format_dhms(val)


class Parser(object):
    """
    A parser class that has configuration and therefore is instanced.
    """
    def parse(self, input, actor=None):
        """
        Parse the input and return the value. Can raise errors.

        @param input: The user input to parse.
        @param actor: If parsing from an object's perspective, the object.
        """


class UnitParser(Parser):
    """
    A parser for quantities expressed with units.
    """

    def __init__(self, dimensions=None):
        self.dimensions = dimensions

    def parse(self, input, actor=None):
        try:
            q = utils.units.parse(input)
        except (utils.units.UndefinedUnitError,
                utils.units.DimensionalityError):
            raise errors.ParseError("Invalid quantity.")
        dims = self.dimensions
        if isinstance(dims, basestring):
            if not q.is_simple_dimension(dims):
                raise errors.ParseError("Invalid %s." % dims)
        elif isinstance(dims, utils.units.UnitsContainer):
            if dims != q.dimensionality:
                raise errors.ParseError("Units not compatible with %s." % dims)
        return q


class MatchObject(Parser):
    """
    Parser to match an object from the perspective of another object.
    """
    def __init__(self, cls=StoredObject, err=True, search_for=None,
                 show=False):
        """
        @param cls: Matching object must be of this objClass.
        @param err: If True, raises a L{mudsling.errors.MatchError}.
        @param search_for: String describing what is being sought.
        @param show: If true, includes list of objects for ambiguous matches.
        """
        self.objClass = cls
        self.err = err
        self.search_for = search_for
        self.show = show

    def _match(self, obj, input):
        return obj.match_object(input, cls=self.objClass, err=False)

    def parse(self, input, actor=None):
        if actor is None:
            return False
        m = self._match(actor, input)
        if len(m) == 1:
            return m[0]
        else:
            msg = match.match_failed(
                matches=m,
                search=input,
                search_for=self.search_for,
                show=self.show
            )
            err = errors.AmbiguousMatch(msg) if m else errors.FailedMatch(msg)
            if self.err:
                raise err
            else:
                return err


class MatchOwnContents(MatchObject):
    """
    Parser to match an object inside the object doing the matching.
    """
    def _match(self, obj, input):
        return obj.match_contents(input, cls=self.objClass, err=False)


class MatchOtherContents(MatchObject):
    """
    Parser to match the contents of a specific object.
    """
    def __init__(self, container, cls=StoredObject, err=True, search_for=None,
                 show=False):
        self.container = container
        super(MatchOtherContents, self).__init__(cls, err, search_for, show)

    def _match(self, obj, input):
        return self.container.match_contents(input, cls=self.objClass,
                                             err=False)


class MatchChildren(MatchObject):
    """
    Parser to match an object among the children of a given type.
    """
    def _match(self, obj, input):
        return obj.db.match_children(input, self.objClass)


class MatchDescendants(MatchObject):
    """
    Parser to match an object among the descendants of a given type.
    """
    def _match(self, obj, input):
        return obj.db.match_descendants(input, self.objClass)
