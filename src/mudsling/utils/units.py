import sys

import pint
from pint.quantity import _Quantity

ureg = pint.UnitRegistry()


def _build_quantity(value, units):
    return Quantity(value, units)


class Quantity(_Quantity):
    __slots__ = ()
    _REGISTRY = ureg
    force_ndarray = False

    def __reduce__(self):
        # Smaller pickle size, less class dependency in pickle file.
        return _build_quantity, (self.magnitude, str(self.units))


ureg.Quantity = Quantity
ureg._build_quantity = _build_quantity

# Replace module with unit registry. Hack that is semi-sanctioned.
# See: http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
# See: http://stackoverflow.com/questions/2447353/getattr-on-a-module
sys.modules[__name__] = ureg
