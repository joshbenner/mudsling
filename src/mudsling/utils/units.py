import sys
import re

import pint
from pint.quantity import _Quantity


def _build_quantity(value, units):
    return Quantity(value, units)


class Quantity(_Quantity):
    __slots__ = ()
    _REGISTRY = None
    force_ndarray = False

    def __reduce__(self):
        # Smaller pickle size, less class dependency in pickle file.
        return _build_quantity, (self.magnitude, str(self.units))


class UnitRegistry(pint.UnitRegistry):
    """
    An instance of this class will replace sys.modules[__name__].
    """
    # unit_re = re.compile(r'(?P<magnitude>\d*\.?\d+) *(?P<unit>[^\d]+),?')
    multi_expr_re = re.compile(r'(\d*\.?\d+) *([^\d,]+) *,? *')
    expr_re = re.compile(r'^(\d*\.?\d+) *(.+)$')
    unit_aliases = {
        # Pad out and comma to be sure things are formatted right.
        '"': ' inch, ',
        "'": ' foot, ',
    }
    Quantity = Quantity
    _build_quantity = _build_quantity
    pint = pint

    def __init__(self):
        super(UnitRegistry, self).__init__()
        self.Quantity._REGISTRY = self

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
