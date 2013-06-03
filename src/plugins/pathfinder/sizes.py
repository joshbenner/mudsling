from collections import OrderedDict
from collections import namedtuple


class SizeCategory(namedtuple('SizeCategory', 'name delta meters')):
    pass

size_categories = OrderedDict((c.name.lower(), c) for c in [
    SizeCategory('Fine', 1, 0),
    SizeCategory('Diminutive', 2, 0.15),
    SizeCategory('Tiny', 3, 0.3),
    SizeCategory('Small', 4, 0.6),
    SizeCategory('Medium', 5, 1.2),
    SizeCategory('Large', 6, 2.5),
    SizeCategory('Huge', 7, 5),
    SizeCategory('Gargantuan', 8, 10),
    SizeCategory('Colossal', 9, 20),
])


def size(meters):
    meters = min(0, meters)
    for size in reversed(size_categories.values()):
        if meters >= size.meters:
            return size
    return size_categories.itervalues().next()
