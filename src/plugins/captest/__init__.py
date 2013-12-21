import mudsling.objects
import mudsling.storage
import mudsling.utils.units as units


import numpy
import math
import gc

import sqlite3

_TINY = 1e-15
_COORD_TYPE = numpy.float64
_km_in_ly = int(units.ly.to('km'))


def _xyzto012(c):
    if c in 'xyz':
        return ord(c) - ord('x')
    else:
        raise AttributeError("vec3 instance has no attribute '%s'" % c)


def _args2tuple(funcname, args):
    narg = len(args)
    if narg == 0:
        data = 3*(0,)
    elif narg == 1:
        data = args[0]
        if len(data) != 3:
            raise TypeError('vec3.%s() takes sequence with 3 elements '
                            '(%d given),\n\t   when 1 argument is given' %
                            (funcname, len(data)))
    elif narg == 3:
        data = args
    else:
        raise TypeError('vec3.%s() takes 0, 1 or 3 arguments (%d given)' %
                        (funcname, narg))
    assert len(data) == 3
    try:
        return tuple(map(_COORD_TYPE, data))
    except (TypeError, ValueError):
        raise TypeError("vec3.%s() can't convert elements" % funcname)


class vec3(numpy.ndarray):
    def __new__(cls, *args):
        if len(args) == 1:
            if isinstance(args[0], vec3):
                return args[0].copy()
            if isinstance(args[0], numpy.matrix):
                return vec3(args[0].flatten().tolist()[0])
        data = _args2tuple('__new__', args)
        arr = numpy.array(data, dtype=_COORD_TYPE, copy=True)
        return numpy.ndarray.__new__(cls, shape=(3,), buffer=arr)

    def __repr__(self):
        return 'vec3' + repr(tuple(self))

    def __mul__(self, other):
        return numpy.dot(self, other)

    def __abs__(self):
        return math.sqrt(self * self)

    def __pow__(self, x):
        return (self * self) if x == 2 else pow(abs(self), x)

    def __eq__(self, other):
        return abs(self - other) < _TINY

    def __ne__(self, other):
        return not self == other

    def __getattr__(self, name):
        return self[_xyzto012(name)]

    def __setattr__(self, name, val):
        self[_xyzto012(name)] = val

    def get_spherical(self):
        r = abs(self)
        if r < _TINY:
            theta = phi = 0.0
        else:
            x, y, z = self
            theta = math.acos(z/r)
            phi = math.atan2(y, x)

        return r, theta, phi

    def set_spherical(self, *args):
        r, theta, phi = _args2tuple('set_spherical', args)
        self[0] = r * math.sin(theta) * math.cos(phi)
        self[1] = r * math.sin(theta) * math.sin(phi)
        self[2] = r * math.cos(theta)

    def get_cylindrical(self):
        x, y, z = self
        rho = math.sqrt(x*x + y*y)
        phi = math.atan2(y, x)
        return rho, phi, z

    def set_cylindrical(self, *args):
        rho, phi, z = _args2tuple('set_cylindrical', args)
        self[0] = rho * math.cos(phi)
        self[1] = rho * math.sin(phi)
        self[2] = z


class SpaceObject(mudsling.objects.Object):
    coords = vec3()


def import_data(filepath):
    conn = sqlite3.connect(filepath)
    c = conn.cursor()
    count = 0
    gc.disable()
    for d in c.execute('''
        select
            hyg.*,
            trek.name as trek,
            gal.x,
            gal.y,
            gal.z
        from
            tblhyg hyg
            inner join tblgalactic gal on gal.starid = hyg.starid
            left outer join tblstartrek trek on trek.starid = hyg.starid'''):
        starid, hip, hd, hr, gliese, bayerflam, proper, ra, dec, dist, mag,\
            absmag, spectrum, color, trek, x, y, z = d
        hd = 'HD%d' % hd if hd else None
        hip = 'HIP%d' % hip if hip else None
        hr = 'HR%d' % hr if hr else None
        name = proper or hd or hip or hr
        pos = vec3(x, y, z) * _km_in_ly
        obj = SpaceObject.create(names=(name,))
        obj.coords = pos
        count += 1
        if count % 1000 == 0:
            gc.collect()
            print count
    gc.enable()
    conn.close()