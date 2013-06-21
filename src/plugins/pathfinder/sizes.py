from collections import OrderedDict

from mudsling.utils import units


class SizeCategory(object):
    name = ''
    delta = 0  # Used to measure relative size categories.
    space = 0
    size_modifier = 0
    special_size_modifier = 0
    stealth_modifier = 0
    length = (0, 0)
    weight = (0, 0)


inch = inches = units.inch
foot = feet = units.foot
lb = lbs = units.pound
tons = units.tons


class Fine(SizeCategory):
    name = 'Fine'
    delta = -4
    space = 0.5 * feet
    size_modifier = 8
    special_size_modifier = -8
    stealth_modifier = 16
    length = (0 * inches, 6 * inches)
    weight = (0 * lbs, 0.125 * lbs)


class Diminutive(SizeCategory):
    name = 'Diminutive'
    delta = -3
    space = 1 * foot
    size_modifier = 4
    special_size_modifier = -4
    stealth_modifier = 12
    length = (6 * inches, 1 * foot)
    weight = (0.125 * lbs, 1 * lb)


class Tiny(SizeCategory):
    name = 'Tiny'
    delta = -2
    size_modifier = 2
    special_size_modifier = -2
    stealth_modifier = 8
    space = 2.5 * feet
    length = (1 * foot, 2 * feet)
    weight = (1 * lb, 8 * lbs)


class Small(SizeCategory):
    name = 'Small'
    delta = -1
    size_modifier = 1
    special_size_modifier = -1
    stealth_modifier = 4
    space = 5 * feet
    length = (2 * feet, 4 * feet)
    weight = (8 * lbs, 60 * lbs)


class Medium(SizeCategory):
    name = 'Medium'
    delta = 0
    size_modifier = 0
    special_size_modifier = 0
    stealth_modifier = 0
    space = 5 * feet
    length = (4 * feet, 8 * feet)
    weight = (60 * lbs, 500 * lbs)


class Large(SizeCategory):
    name = 'Large'
    delta = 1
    size_modifier = -1
    special_size_modifier = 1
    stealth_modifier = -4
    space = 10 * feet
    length = (8 * feet, 16 * feet)
    weight = (500 * lbs, 4000 * lbs)


class Huge(SizeCategory):
    name = 'Huge'
    delta = 2
    size_modifier = -2
    special_size_modifier = 2
    stealth_modifier = -8
    space = 15 * feet
    length = (16 * feet, 32 * feet)
    weight = (2 * tons, 16 * tons)


class Gargantuan(SizeCategory):
    name = 'Gargantuan'
    delta = 3
    size_modifier = -4
    special_size_modifier = 4
    stealth_modifier = -12
    space = 20 * feet
    length = (32 * feet, 64 * feet)
    weight = (16 * tons, 125 * tons)


class Colossal(SizeCategory):
    name = 'Colossal'
    delta = 4
    size_modifier = -8
    special_size_modifier = 8
    stealth_modifier = -16
    space = 30 * feet
    length = (64 * feet, None)
    weight = (125 * tons, None)


del inch, inches, foot, feet, lb, lbs, tons

size_categories = OrderedDict((c.name.lower(), c) for c in [
    Fine, Diminutive, Tiny, Small, Medium, Large, Huge, Gargantuan, Colossal
])


def size(dimension):
    for size in reversed(size_categories.values()):
        if dimension >= size.length[0]:
            return size
    return size_categories.itervalues().next()
