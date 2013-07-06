# -*- coding: utf-8 -*-
import sys
import re
import pkg_resources
import math

import pint
from pint.unit import PrefixDefinition, UnitDefinition, ScaleConverter
from pint.unit import UnitsContainer
from pint import UndefinedUnitError, DimensionalityError
from pint.quantity import _Quantity as __Quantity


class _Quantity(__Quantity):
    __slots__ = ()
    _REGISTRY = None
    force_ndarray = False

    def __reduce__(self):
        # Smaller pickle size, less class dependency in pickle file.
        return self._REGISTRY.Quantity, (self.magnitude, str(self.units))

    def is_simple_dimension(self, d):
        """
        Determine if quantity consists
        """
        d = '[%s]' % d.strip(' []')
        return (len(self.dimensionality) == 1
                and self.dimensionality[d] == 1.0)


class UnitRegistry(pint.UnitRegistry):
    """
    An instance of this class will replace sys.modules[__name__].
    """
    multi_expr_re = re.compile(r'(\d*\.?\d+) *([^\d,]+) *,? *')
    expr_re = re.compile(r'^(\d*\.?\d+) *(.+)$')
    unit_aliases = {
        # Pad out and comma to be sure things are formatted right.
        '"': ' inch, ',
        "'": ' foot, ',
    }
    UnitsContainer = UnitsContainer
    UndefinedUnitError = UndefinedUnitError
    DimensionalityError = DimensionalityError

    # Override init so we can use our own Quantity which is smaller in memory
    # and will pickle efficiently.
    def __init__(self, filename='', default_to_delta=True):
        class Quantity(_Quantity):
            __slots__ = ()
            _REGISTRY = self

        self.Quantity = Quantity
        #: Map dimension name (string) to its definition (DimensionDefinition).
        self._dimensions = {}

        #: Map unit name (string) to its definition (UnitDefinition).
        self._units = {}

        #: Map prefix name (string) to its definition (PrefixDefinition).
        self._prefixes = {'': PrefixDefinition('', '', (), 1)}

        #: Map suffix name (string) to canonical, and unit alias to canonical
        # unit name
        self._suffixes = {'': None, 's': ''}

        #: In the context of a multiplication of units, interpret
        #: non-multiplicative units as their *delta* counterparts.
        self.default_to_delta = default_to_delta

        if filename == '':
            # Purposefully *not* using resource_stream as it may return a
            # StringIO object for which we can't specify the encoding
            data = pkg_resources.resource_string(pint.__name__, 'default_en.txt').decode('utf-8')
            self.load_definitions(data.splitlines())
        elif filename is not None:
            self.load_definitions(filename)

        self.define(UnitDefinition('pi', 'π', (), ScaleConverter(math.pi)))

    def parse(self, input):
        """
        Parse string describing a value into a quantity.

        Examples:
        * 5 feet, 6 inches
        * 2'3"
        * 10 miles/hr
        * 300000 m/s^2

        @param input: The string to parse.
        @rtype: L{Quantity}
        """
        value = None
        for repl in self.unit_aliases.iteritems():
            input = input.replace(*repl)
        for part in input.strip(', ').split(','):
            magstr, _, unitstr = part.strip().partition(' ')
            mag = float(magstr) if ('.' in magstr) else int(magstr)
            v = self.Quantity(mag, unitstr.strip())
            if value is None:
                value = v
            else:
                value += v
        return value

# Replace module with unit registry. Hack that is semi-sanctioned.
# See: http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
# See: http://stackoverflow.com/questions/2447353/getattr-on-a-module
sys.modules[__name__] = UnitRegistry()
