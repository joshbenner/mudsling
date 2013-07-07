from collections import namedtuple

from mudsling.utils import units

Quantity = units.Quantity


class Dimensions(namedtuple('Dimensions', 'l w h units')):
    __slots__ = ()

    def __new__(cls, length=0, width=0, height=0, units='meter'):
        l, w, h = (d.to(units).magnitude if isinstance(d, Quantity) else d
                   for d in (length, width, height))
        return super(Dimensions, cls).__new__(cls, l, w, h, units)

    length = property(lambda self: self._as_quantity('l'))
    width = property(lambda self: self._as_quantity('w'))
    height = property(lambda self: self._as_quantity('h'))

    @property
    def all(self):
        return self.length, self.width, self.height

    def _as_quantity(self, dim, units=None):
        """
        @rtype: L{mudsling.utils.units.Quantity}
        """
        return Quantity(getattr(self, dim), units or self.units)

    def to(self, unit):
        dims = (self.l, self.w, self.h)
        return tuple(self._as_quantity(d).ito(unit) for d in dims)

    @property
    def volume(self):
        return Quantity(self.l * self.w * self.h, self.units ** 3)

    @property
    def dimensionality(self):
        return units.parse_units(self.units)

    def __str__(self):
        u = units.format_dimensions(self.dimensionality.items(),
                                    count=self.l + self.w + self.h)
        return "{}x{}x{} {}".format(self.l, self.w, self.h, u)

    def _replace(self, **kw):
        dims = ('length', 'width', 'height')
        for dim in dims:
            d = dim[0]
            if dim in kw:
                kw[d] = kw[dim]
                del kw[dim]
            if d in kw and isinstance(kw[d], Quantity):
                kw[d] = kw[d].to(kw.get('units', self.units)).magnitude
        if 'units' in kw:
            new_units = kw['units']
            for dim in dims:
                if dim[0] not in kw:
                    kw[dim[0]] = getattr(self, dim).ito(new_units).magnitude
        return super(Dimensions, self)._replace(**kw)
