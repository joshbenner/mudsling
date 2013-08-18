from collections import OrderedDict
import inspect

from mudsling.objects import Object
from mudsling.storage import ObjRef
from mudsling.utils import units
from mudsling.utils.measurements import Dimensions

from mudslingcore.objects import Thing as CoreThing

import pathfinder

from .stats import HasStats
from .events import Event
from .features import HasFeatures
from .sizes import size_categories
from .modifiers import Modifier
from .effects import Effect
from .conditions import Condition


def is_pfobj(obj):
    return (isinstance(obj, PathfinderObject)
            or (isinstance(obj, ObjRef) and obj.isa(PathfinderObject)))


class PathfinderObject(Object, HasStats, HasFeatures):
    _transient_vars = ['_stat_cache']

    cost = 0
    weight = units.Quantity(0, 'gram')
    hardness = 0
    dimensions = Dimensions()
    _size_category = None
    permanent_hit_points = 0
    damage = 0
    effects = []
    conditions = []
    stat_aliases = {
        'hp': 'hit points',
        'thp': 'temporary hit points',
        'mhp': 'max hit points',
        'max hp': 'max hit points',
        'temp hp': 'temporary hit points',
    }
    stat_attributes = {
        'hit_points': 'hit points',
        'max_hp': 'max hit points',
        'temporary_hit_points': 'temporary hit points',
    }

    def __init__(self, **kw):
        # noinspection PyArgumentList
        super(PathfinderObject, self).__init__(**kw)
        self.effects = []
        self.conditions = []

    def _check_attr(self, attr, val):
        if attr not in self.__dict__:
            setattr(self, attr, val)

    @property
    def features(self):
        return list(self.conditions)

    @property
    def remaining_hp(self):
        """:rtype: int"""
        return self.max_hp - self.damage

    @property
    def hp_ratio(self):
        """:rtype: float"""
        hp = float(self.hit_points)
        return float(self.remaining_hp) / hp if hp > 0.0 else 0.0

    @property
    def hp_percent(self):
        """:rtype: float"""
        return self.hp_ratio * 100.0

    @property
    def size_category(self):
        return self._size_category or pathfinder.size(max(self.dimensions.all))

    @size_category.setter
    def size_category(self, val):
        if val not in size_categories.values():
            raise ValueError("Invalid size category.")
        default = pathfinder.size(max(self.dimensions.all))
        if val == default:
            try:
                del self._size_category
            except AttributeError:
                pass  # It's not there, don't worry.
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

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat == 'hit points':
            return self.permanent_hit_points
        elif stat == 'max hit points':
            return self.hit_points + self.temporary_hit_points
        elif stat == 'temporary hit points':
            return 0
        else:
            return super(PathfinderObject, self).get_stat_base(stat,
                                                               resolved=True)

    def apply_effect(self, effect, source=None):
        """
        @type effect: L{pathfinder.effects.Effect}
            or L{pathfinder.effects.Modifier}
        """
        if isinstance(effect, Modifier):
            effect = Effect(effect, source)
        effect.apply_to(self.ref())

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
            effect.remove_from(self)
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

    def add_condition(self, condition, source=None):
        """Add the specified condition to the object.

        :param condition: The condition, condition class, or condition name
            specifying the condition to add to the object.
        :type condition: pathfinder.conditions.Condition or str or type

        :param source: The cause of the condition.
        """
        if isinstance(condition, basestring):
            condition = pathfinder.data.get('condition', condition)
        if inspect.isclass(condition):
            condition = condition(source=source)
        if isinstance(condition, Condition):
            condition.apply_to(self)
        else:
            raise ValueError("Condition must be a string, condition class, or"
                             " condition instance")

    def remove_condition(self, condition):
        """Remove the specified condition.

        :param condition: The condition to remove.
        :type condition: pathfinder.conditions.Condition
        """
        condition.remove_from(self)
        if condition in self.conditions:
            self.conditions.remove(condition)

    def _apply_condition(self, condition):
        self._check_attr('conditions', [])
        if condition not in self.conditions:
            self.conditions.append(condition)

    def get_condition(self, condition, source=None):
        """Retrieve any instances of the condition specified.

        :param condition: The condition name or class to look for.
        :type condition: str or type

        :param source: Limit results to those with a specified source.

        :return: List of conditions of the specified type which are currently
            in effect for this object.
        :rtype: list
        """
        if isinstance(condition, basestring):
            condition = pathfinder.data.get('condition', condition)
        return [c for c in self.conditions
                if c.__class__ == condition
                and (source is None or source == c.source)]

    def has_condition(self, condition):
        """Determine whether or not the object has a specific condition.

        :param condition: The condition in question.
        :type condition: str or Condition subclass

        :return: Whether this object has the specified condition or not.
        :rtype: bool
        """
        return len(self.get_condition(condition)) > 0

    def has_any_condition(self, conditions):
        for condition in conditions:
            if self.has_condition(condition):
                return True
        return False

    def take_damage(self, damage):
        pass


class Thing(CoreThing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """
