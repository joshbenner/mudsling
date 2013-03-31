"""
Sequence utilities.
"""
from itertools import chain
import operator


class CaselessDict:
    """
    Case-insensitive dictionary.

    Emulates a normal Python dictionary but with keys which can accept the
    lower() method (typically strings). Accesses to the dictionary are
    case-insensitive but keys returned from the dictionary are always in the
    original case.

    @author: Chris Hobbs
    @see: U{http://code.activestate.com/recipes/66315/#c5}
    """
    def __init__(self, inDict=None):
        """
        Constructor: takes conventional dictionary as input (or nothing).
        """
        self.dict = {}
        if inDict is not None:
            for key in inDict:
                k = key.lower()
                self.dict[k] = (key, inDict[key])
        self.keyList = self.dict.keys()
        return

    def __iter__(self):
        self.iterPosition = 0
        return self

    def next(self):
        if self.iterPosition >= len(self.keyList):
            raise StopIteration
        x = self.dict[self.keyList[self.iterPosition]][0]
        self.iterPosition += 1
        return x

    def __getitem__(self, key):
        k = key.lower()
        return self.dict[k][1]

    def __setitem__(self, key, value):
        k = key.lower()
        self.dict[k] = (key, value)
        self.keyList = self.dict.keys()

    def has_key(self, key):
        k = key.lower()
        return k in self.keyList

    def __len__(self):
        return len(self.dict)

    def keys(self):
        return [v[0] for v in self.dict.values()]

    def values(self):
        return [v[1] for v in self.dict.values()]

    def items(self):
        return self.dict.values()

    def __contains__(self, item):
        return item.lower() in self.dict

    def __repr__(self):
        items = ", ".join([("%r: %r" % (k, v)) for k, v in self.items()])
        return "{%s}" % items

    def __str__(self):
        return repr(self)

    def get(self, key, alt):
        if key in self:
            return self.__getitem__(key)
        return alt

    def iteritems(self):
        return (v for v in self.dict.values())


def unique(seq):
    """
    Return a list of unique values in the iterable, preserving their order.

    By Dave Kirby

    U{http://www.peterbe.com/plog/uniqifiers-benchmark}

    @rtype: C{list}
    """
    seen = set()
    add = seen.add
    return [x for x in seq if x not in seen and not add(x)]


def dictMerge(*dicts):
    """Efficient merge of an arbitrary number of dictionaries."""
    return dict(chain(*[d.iteritems() for d in dicts]))


def isSequence(val):
    return hasattr(val, '__iter__')


def flattenList(lst):
    """
    Flattens one level of a list of lists.
    """
    return reduce(operator.iadd, lst, [])


def flatten(iterable):
    """
    Flattens an iterable of arbitrary depth with a mixture of iterable and non-
    iterable elements recursively.

    Discards dictionary keys.

    Recursive, possibly inefficient. Use with care.

    @param iterable: The iterable to flatten into a list.
    @return: A flattened list representation of the provided iterable.
    @rtype: C{list}
    """
    out = []
    if isinstance(iterable, dict):
        iterable = iterable.itervalues()
    for e in iterable:
        if isSequence(e):
            for ee in flatten(e):
                out.append(ee)
        else:
            out.append(e)
    return out
