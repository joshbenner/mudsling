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

    def __str__(self):
        u = self._REGISTRY.format_dimensions(self._units.items(),
                                             count=self._magnitude)
        return '{} {}'.format(self._magnitude, u)

    def short(self):
        u = self._REGISTRY.format_dimensions(self._units.items(), short=True,
                                             product_fmt='*', division_fmt='/')
        return '{} {}'.format(self._magnitude, u)

    def graduated(self, strings=False, short=False, limit=None):
        if len(self._units) != 1 or not round(self._magnitude, 14):
            parts = [self]
        else:
            native_unit = str(self._units.keys()[0])
            scale = None
            for grad_units in self._REGISTRY.graduated_units:
                if native_unit in grad_units:
                    scale = grad_units
                    break
            if scale is None:
                parts = [self]
            else:
                parts = []
                remainder = self.to(self._units)
                Q = self.__class__
                for i, unit in enumerate(scale):
                    last = (i == len(scale) - 1)
                    as_unit = remainder.to(unit)
                    if as_unit._magnitude >= 1 or (last and not parts):
                        # Compromise at 14 digits to avoid float precision.
                        value = int(round(as_unit._magnitude, 14))
                        if value:
                            part = Q(value, unit)
                            parts.append(part)
                            remainder -= part
                            if limit and len(parts) >= limit:
                                break
        if strings:
            return [(p.short() if short else str(p)) for p in parts]
        else:
            return parts


class UnitRegistry(pint.UnitRegistry):
    """
    An instance of this class will replace sys.modules[__name__].
    """
    from mudsling.utils.string import inflection
    inflection = inflection

    multi_expr_re = re.compile(r'(\d*\.?\d+) *([^\d,]+) *,? *')
    expr_re = re.compile(r'^(\d*\.?\d+) *(.+)$')
    unit_aliases = {
        # Pad out and comma to be sure things are formatted right.
        '"': ' inch, ',
        "'": ' foot, ',
    }

    _pint = pint
    UnitsContainer = UnitsContainer
    UndefinedUnitError = UndefinedUnitError
    DimensionalityError = DimensionalityError

    # Units used together when displaying a graduated set of quantities.
    graduated_units = (
        ('mile', 'foot', 'inch'),
        ('kilometer', 'meter', 'centimeter', 'millimeter', 'micrometer',
         'nanometer'),
        ('week', 'day', 'hour', 'minute', 'second', 'millisecond',
         'microsecond', 'nanosecond'),
        ('ton', 'pound', 'ounce'),
        ('kilogram', 'gram')
    )

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
            data = pkg_resources\
                .resource_string(__name__, 'unit_definitions.txt')\
                .decode('utf-8')
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

    def format_dimensions(self, items, as_ratio=True, single_denominator=False,
                          product_fmt=' * ', division_fmt=' / ',
                          power_fmt='{}^{}', parentheses_fmt='({})',
                          exp_call=lambda x: '{:n}'.format(x), count=1,
                          short=False):
        """Format a list of (name, exponent) pairs.

        :param items: a list of (name, exponent) pairs.
        :param as_ratio: True to display as ratio, False as negative powers.
        :param single_denominator: all with terms with negative exponents are
                                   collected together.
        :param product_fmt: the format used for multiplication.
        :param division_fmt: the format used for division.
        :param power_fmt: the format used for exponentiation.
        :param parentheses_fmt: the format used for parenthesis.

        :return: the formula as a string.
        """
        _join = self._pint.util._join
        if as_ratio:
            fun = lambda x: exp_call(abs(x))
        else:
            fun = exp_call

        pos_terms, neg_terms = [], []

        for key, value in sorted(items):
            if short:
                key = self.get_symbol(key)
            if value == 1:
                pos_terms.append(key)
            elif value > 1:
                pos_terms.append(power_fmt.format(key, fun(value)))
            elif value == -1:
                neg_terms.append(key)
            else:
                neg_terms.append(power_fmt.format(key, fun(value)))

        if pos_terms:
            if (count != 1) and not short:
                pos_terms[-1] = self.inflection.plural_noun(pos_terms[-1])
            pos_ret = _join(product_fmt, pos_terms)
        elif as_ratio and neg_terms:
            pos_ret = '1'
        else:
            pos_ret = ''

        if not neg_terms:
            out = pos_ret
        else:
            if as_ratio:
                if single_denominator:
                    neg_ret = _join(product_fmt, neg_terms)
                    if len(neg_terms) > 1:
                        neg_ret = parentheses_fmt.format(neg_ret)
                else:
                    neg_ret = _join(division_fmt, neg_terms)
            else:
                neg_ret = product_fmt.join(neg_terms)
            out = _join(division_fmt, [pos_ret, neg_ret])
        return out.replace('_', ' ')

# Replace module with unit registry. Hack that is semi-sanctioned.
# See: http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
# See: http://stackoverflow.com/questions/2447353/getattr-on-a-module
sys.modules[__name__] = UnitRegistry()
