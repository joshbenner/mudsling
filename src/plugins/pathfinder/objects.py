from collections import OrderedDict

from mudsling.objects import Object
from mudsling.storage import ObjRef

from mudslingcore.objects import Thing as CoreThing

import pathfinder

from .stats import HasStats
from .events import Event
from .features import HasFeatures
from .sizes import SizeCategory
from .modifiers import Modifier
from .effects import Effect


def is_pfobj(obj):
    return (isinstance(obj, PathfinderObject)
            or (isinstance(obj, ObjRef) and obj.isa(PathfinderObject)))


class PathfinderObject(Object, HasStats, HasFeatures):
    cost = 0
    weight = 0
    hardness = 0
    dimensions = (0, 0, 0)
    _size_category = None
    hitpoints = 0
    temporary_hitpoints = 0
    damage = 0
    effects = []

    def __init__(self, **kw):
        # noinspection PyArgumentList
        super(PathfinderObject, self).__init__(**kw)
        self.effects = []

    def _check_attr(self, attr, val):
        if attr not in self.__dict__:
            setattr(self, attr, val)

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

    def event_responders(self, event):
        responders = super(PathfinderObject, self).event_responders(event)
        responders.extend(self.effects)
        return responders

    def get_stat_modifiers(self, stat, **kw):
        """
        @rtype: L{collections.OrderedDict}
        """
        stat, tags = self.resolve_stat_name(stat)
        event = Event('stat mods', stat=stat, tags=tags, **kw)
        event.modifiers = OrderedDict()
        self.trigger_event(event)
        return event.modifiers

    def apply_effect(self, effect, source=None):
        """
        @type effect: L{pathfinder.effects.Effect}
            or L{pathfinder.effects.Modifier}
        """
        if isinstance(effect, Modifier):
            effect = Effect(effect, source)
        effect.apply_to(self)

    def _apply_effect(self, effect):
        """
        @type effect: L{pathfinder.effects.Effect}
        """
        self._check_attr('effects', [])
        self.effects.append(effect)

    def remove_effect(self, effect):
        self._check_attr('effects', [])
        if effect in self.effects:
            self.effects.remove(effect)
            return True
        return False

    def remove_effects(self, effects):
        removed = set()
        for e in effects:
            if self.remove_effect(e):
                removed.add(e)
        return removed

    def remove_effects_by_source(self, source):
        remove = set()
        for e in self.effects:
            if e.source == source:
                remove.add(e)
        return self.remove_effects(remove)

    def take_damage(self, damage):
        pass


class Thing(CoreThing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """
