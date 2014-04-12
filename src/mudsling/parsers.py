"""
Parsers are classes used to convert from strings representing a value to
the python value, and back again. The most straightforward case is converting
to/from input and a python value.
"""
import re

from mudsling import registry
from mudsling import errors
from mudsling import match
from mudsling.storage import StoredObject

from mudsling import utils
import mudsling.utils.time
import mudsling.utils.units
import mudsling.utils.measurements


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
        #return registry.classes.get_class_name(val) or cls.invalid_str
        mod = val.__module__
        if mod == '__builtin__':
            mod = ''
        else:
            mod += '.'
        return mod + val.__name__


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

    def unparse(self, value):
        return str(value)


class UnitParser(Parser):
    """
    A parser for quantities expressed with units.
    """

    def __init__(self, dimensions=None):
        self.dimensions = dimensions

    def parse(self, input, actor=None):
        q = UnitStaticParser.parse(input)
        dims = self.dimensions
        if isinstance(dims, basestring):
            if not q.is_simple_dimension(dims):
                raise errors.ParseError("Invalid %s." % dims)
        elif isinstance(dims, utils.units.UnitsContainer):
            if dims != q.dimensionality:
                raise errors.ParseError("Units not compatible with %s." % dims)
        return q


class UnitStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        try:
            q = utils.units.parse(input)
        except ValueError:
            raise errors.ParseError("Invalid quantity.")
        return q


class DimensionsStaticParser(StaticParser):
    """
    A parser for length, width, and height expressed as units.

    Syntax: <length><units>x<width><units>x<height><units>
    """
    regex = re.compile(r'(?P<length>\d*\.?\d+(?: *[a-zA-Z]+)?) *x *'
                       r'(?P<width>\d*\.?\d+(?: *[a-zA-Z]+)?) *x *'
                       r'(?P<height>\d*\.?\d+(?: *[a-zA-Z]+)?)')

    @classmethod
    def parse(cls, input):
        m = cls.regex.match(input)
        if not m:
            raise errors.ParseError('Invalid dimension syntax.')
        inputs = m.groupdict()
        values = {}
        default_unit = None
        for dim in inputs.iterkeys():
            try:
                value = utils.units.parse(inputs[dim])
            except ValueError:
                raise errors.ParseError('Invalid quantity: %s' % inputs[dim])
            values[dim] = value
            if default_unit is None and not value.unitless:
                default_unit = value.units
        if default_unit is None:
            raise errors.ParseError('No units specified.')
        for dim in inputs.iterkeys():
            if values[dim].unitless:
                values[dim] = utils.units.Quantity(values[dim].magnitude,
                                                   default_unit)
        return mudsling.utils.measurements.Dimensions(
            length=values['length'],
            width=values['width'],
            height=values['height'],
            units=str(default_unit.keys()[0])
        )


class MatchObject(Parser):
    """
    Parser to match an object from the perspective of another object.
    """
    def __init__(self, cls=StoredObject, err=True, search_for=None,
                 show=False, context=True):
        """
        :param cls: Matching object must be of this objClass.
        :param err: If True, raises a L{mudsling.errors.MatchError}.
        :param search_for: String describing what is being sought.
        :param show: If true, includes list of objects for ambiguous matches.
        :param context: If true, limit matching to object's context.
        """
        self.objClass = cls
        self.err = err
        self.search_for = search_for
        self.show = show
        self.context = context

    def _match(self, obj, input):
        try:
            f = obj.match_context if self.context else obj.match_object
        except AttributeError:
            return []
        return f(input, cls=self.objClass, err=False)

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
                show=self.show,
                names=actor.name_for if actor is not None else str
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
