from collections import OrderedDict
import inspect

import mudsling.objects
import mudsling.storage
import mudsling.utils.measurements
import mudsling.match
import mudsling.errors

import mudslingcore.objects as core_objects
import mudslingcore.topography as core_topography

import pathfinder
import pathfinder.sizes
import pathfinder.stats
import pathfinder.features
import pathfinder.modifiers
import pathfinder.effects
import pathfinder.conditions
import pathfinder.combat


def is_pfobj(obj):
    return (isinstance(obj, PathfinderObject)
            or (isinstance(obj, mudsling.storage.ObjRef)
                and obj.isa(PathfinderObject)))


class PathfinderObject(mudsling.objects.Object,
                       pathfinder.stats.HasStats,
                       pathfinder.features.HasFeatures):
    _transient_vars = ['_stat_cache']

    cost = 0
    weight = mudsling.utils.units.Quantity(0, 'gram')
    hardness = 0
    dimensions = mudsling.utils.measurements.Dimensions()
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
        return (self._size_category
                or pathfinder.sizes.size(max(self.dimensions.all)))

    @size_category.setter
    def size_category(self, val):
        if val not in pathfinder.sizes.size_categories.values():
            raise ValueError("Invalid size category.")
        default = pathfinder.sizes.size(max(self.dimensions.all))
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
        :rtype: collections.OrderedDict
        """
        stat, tags = self.resolve_stat_name(stat)
        event = self.trigger_event('stat mods', stat=stat, tags=tags,
                                   modifiers=OrderedDict(), **kw)
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
        if isinstance(effect, pathfinder.modifiers.Modifier):
            effect = pathfinder.effects.Effect(effect, source)
        effect.apply_to(self.ref())

    def _apply_effect(self, effect):
        """
        @type effect: L{pathfinder.effects.Effect}
        """
        self._check_attr('effects', [])
        self.effects.append(effect)
        self.trigger_event('effect applied', effect=effect)

    def remove_effect(self, effect):
        self._check_attr('effects', [])
        if effect in self.effects:
            self.effects.remove(effect)
            effect.remove_from(self)
            self.trigger_event('effect removed', effect=effect)
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
        if isinstance(condition, pathfinder.conditions.Condition):
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
            self.trigger_event('condition removed', condition=condition)

    def _add_condition(self, condition):
        self._check_attr('conditions', [])
        if condition not in self.conditions:
            self.conditions.append(condition)
            self.trigger_event('condition added', condition=condition)

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


class Thing(core_objects.Thing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """


class Room(core_topography.Room):
    """
    Pathfinder rooms have 'combat areas' which combatants can be 'near'.
    """

    def combat_areas(self, exclude_self=False):
        """
        Get a list of all combat areas in this room.

        :return: List of all combat areas in room.
        :rtype: list
        """
        areas = list(self.exits)
        areas.extend(c for c in self.contents
                     if c.isa(pathfinder.combat.Combatant))
        if not exclude_self:
            areas.append(self.ref())
        return areas

    def adjacent_combat_areas(self, area):
        """
        Get a list of adjacent combat areas. These represent the combat areas
        that a combatant can move into with a single move action.

        Adjacent areas include the 'open' area (the room itself) and any
        combatants in the specified area.

        :param area: The area whose adjacent areas to retriee.

        :return: List of adjacent combat areas.
        :rtype: list

        :raises: ValueError
            When the area is another combatant, and that combatant's position
            is themself (which would result in infinite recursion).
        """
        if self.db.is_valid(area, pathfinder.combat.Combatant):
            # If positioned near another combatant, adjacency is equivalent to
            # the adjacency of that combatant.
            if area.combat_position == area:
                raise ValueError('Combatant %r is adjacent to self' % area)
            return self.adjacent_combat_areas(area.combat_position)
        adjacent = [c for c in self.contents
                    if c.isa(pathfinder.combat.Combatant)
                    and c.combat_position == area]
        if area == self or area == self.ref():
            # All exits are adjacent to the 'open' area.
            adjacent.extend(self.exits)
        else:
            # The open area is adjacent to all areas.
            adjacent.append(self.ref())
        return adjacent

    def match_combat_area(self, input):
        """
        Match a combat area.

        :param input: The string used to match a combat area.
        :type input: str

        :return: A combat area if found.

        :raises: AmbiguousMatch, FailedMatch
        """
        if input in ('open', 'the open', 'the clear', 'nothing'):
            return self.ref()
        matches = mudsling.match.match_objlist(
            input,
            self.combat_areas(exclude_self=True)
        )
        if len(matches) == 1:
            return matches[0].ref()
        else:
            msg = mudsling.match.match_failed(matches, search=input,
                                              search_for='combat area',
                                              show=True)
            if len(matches) > 1:
                raise mudsling.errors.AmbiguousMatch(msg=msg)
            else:
                raise mudsling.errors.FailedMatch(msg=msg)
