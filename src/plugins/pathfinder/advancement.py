"""
Pathfinder XP advancement tables. The fast and slow progressions are not quite
exactly the same as what's in the PRD, which deviates from a consistent formula
for some of its rounding.
"""
from math import floor, sqrt, log10

import pathfinder


def round_down(n, nearest=1):
    return n - (n % nearest)


def round_up(n, nearest=1):
    return n if n % nearest == 0 else n + nearest - n % nearest


def round_target(n):
    if n:
        return pow(10, floor(log10(n) - 1))
    else:
        return 1


def medium(l):
    return round((2000 * (pow(2, floor(l / 2)) - 1) + 3000 * (pow(2, floor((l - 1) / 2)) - 1)) / pow(10, floor(sqrt(l - 1)) + 1) * 2, 0) / 2 * pow(10, floor(sqrt(l - 1)) + 1)


def fast(l):
    m = medium(l)
    return round_down(m / 1.5, round_target(m))


def slow(l):
    m = medium(l)
    return round_up(m * 1.5, round_target(m))


tables = {
    'slow': tuple([int(slow(x)) for x in xrange(1, 21)]),
    'medium': tuple([int(medium(x)) for x in xrange(1, 21)]),
    'fast': tuple([int(fast(x)) for x in xrange(1, 21)]),
}


def active_table():
    active_table_name = pathfinder.config.getdefault('advancement table',
                                                     default='medium')
    if active_table_name not in tables:
        active_table_name = 'medium'
    return tables[active_table_name]
