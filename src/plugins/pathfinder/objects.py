from mudslingcore.objects import Thing as CoreThing
from mudslingcore.objects import Character as CoreCharacter

import pathfinder

from .stats import HasStats
from .events import HasEvents
from .sizes import SizeCategory


class PathfinderObject(HasStats, HasEvents):
    cost = 0
    weight = 0
    hardness = 0
    dimensions = [0, 0, 0]
    _size_category = None
    hitpoints = 0
    temporary_hitpoints = 0
    damage = 0

    @property
    def max_hp(self):
        return self.hitpoints + self.temporary_hitpoints

    @property
    def hp(self):
        return self.max_hp - self.damage

    @property
    def size_category(self):
        return self._size_category or pathfinder.size(max(self.dimensions))

    @size_category.setter
    def size_category(self, val):
        if not isinstance(val, SizeCategory):
            raise ValueError("Size categories must be of type SizeCategory.")
        default = pathfinder.size(max(self.dimensions))
        if val == default:
            del self._size_category
        else:
            self._size_category = val

    def get_stat_modifiers(self, stat):
        """
        @rtype: L{collections.OrderedDict}
        """


class Thing(CoreThing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """


class Character(CoreCharacter, PathfinderObject):
    """
    A Pathfinder-enabled character/creature/etc.
    """
