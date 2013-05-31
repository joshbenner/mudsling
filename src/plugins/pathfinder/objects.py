from mudsling.storage import Persistent

from mudslingcore.objects import Thing as CoreThing

import pathfinder


class PathfinderObject(Persistent):
    cost = 0
    weight = 0
    hardness = 0
    dimensions = [0, 0, 0]
    _size_category = None
    hitpoints = 0

    @property
    def size_category(self):
        return self._size_category or pathfinder.size(max(self.dimensions))

    @size_category.setter
    def size_category(self, val):
        if not isinstance(val, pathfinder.SizeCategory):
            raise ValueError("Size categories must be of type SizeCategory.")
        default = pathfinder.size(max(self.dimensions))
        if val == default:
            del self._size_category
        else:
            self._size_category = val


class Thing(CoreThing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """

