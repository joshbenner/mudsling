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
        dims = ('l', 'w', 'h')
        return Dimensions(*[self._as_quantity(d).ito(unit) for d in dims],
                          units=unit)

    @property
    def volume(self):
        unit = units[self.units] if isinstance(self.units, str) else self.units
        return Quantity(self.l * self.w * self.h, unit ** 3)

    @property
    def surface_area(self):
        """
        Simplistic surface area based only on rectangular prism representation
        of the dimensions.
        """
        l, w, h = self.all
        return 2 * l * w + 2 * w * h + 2 * l * h

    @property
    def dimensionality(self):
        return units.parse_units(self.units)

    def __str__(self):
        u = units.format_dimensions(self.dimensionality.items(), short=True,
                                    count=self.l + self.w + self.h)
        return "{}x{}x{} {}".format(self.l, self.w, self.h, u)

    def __repr__(self):
        return 'Dimensions: %s' % str(self)

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
                    q = getattr(self, dim)
                    q.ito(new_units)
                    kw[dim[0]] = q.magnitude
        return super(Dimensions, self)._replace(**kw)

    def smallest_dimension(self):
        smallest_dim = 'l'
        smallest_val = self.l
        for dim in ('w', 'h'):
            val = getattr(self, dim)
            if val < smallest_val:
                smallest_dim = dim
                smallest_val = val
        return smallest_dim, smallest_val
