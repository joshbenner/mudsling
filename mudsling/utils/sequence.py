"""
Sequence utilities.
"""


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

