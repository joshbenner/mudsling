from collections import OrderedDict
import inspect

import mudsling.objects
import mudsling.storage
import mudsling.utils.units as units
import mudsling.utils.measurements
import mudsling.match
import mudsling.errors
import mudsling.commands

from icmoney import Money
import dice

import pathfinder
import pathfinder.events
import pathfinder.stats
import pathfinder.features
import pathfinder.modifiers
import pathfinder.effects
import pathfinder.conditions
import pathfinder.damage


def is_pfobj(obj):
    return (isinstance(obj, PathfinderObject)
            or (isinstance(obj, mudsling.storage.ObjRef)
                and obj.isa(PathfinderObject)))


class PathfinderObject(mudsling.objects.Object,
                       pathfinder.stats.HasStats,
                       pathfinder.features.HasFeatures):
    """
    :ivar conditions: The condition instances applied to this object.
    :type conditions: list of pathfinder.conditions.Condition
    """
    _transient_vars = ['_stat_cache']

    cost = Money(0, 'gp')
    weight = mudsling.utils.units.Quantity(0, 'gram')
    hardness = 0
    dimensions = mudsling.utils.measurements.Dimensions()
    _size_category = None
    permanent_hit_points = 0
    damage = 0
    nonlethal_damage = 0
    _effects = []
    _conditions = []
    nonlethal_immunity = True
    critical_immunity = True
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
        self._effects = []
        #: :type: list of pathfinder.conditions.Condition
        self._conditions = []

    def _check_attr(self, attr, val):
        if attr not in self.__dict__:
            setattr(self, attr, val)

    def rpg_notice(self, *parts):
        """
        Notify the room of RPG information.

        **Coloring:**

            :Prefix: magenta
            :Character names: cyan
            :Actions: yellow
            :Rolls: magenta
        """
        # todo: Only show this to people who want it.
        if not isinstance(parts, list):
            parts = list(parts)
        newparts = ['{y%%: {n']
        for i, part in enumerate(parts):
            color = '{n'
            if is_pfobj(part):
                color = '{c'
            elif isinstance(part, dice.Roll):
                color = '{m'
            elif isinstance(part, (pathfinder.damage.Damage,
                                   pathfinder.RollResult)):
                color = '{m'
                part = part.full_desc
                part = part.replace(' = ', ' {n={y ')
            elif isinstance(part, tuple):
                part_type, part = part
                if part_type == 'action':
                    color = '{y'
                elif part_type == 'roll':
                    color = '{m'
            newparts.extend((color, part))
        self.emit(newparts)

    def pf_roll(self, roll, mods=None, state=None, **vars):
        """
        Perform a Pathfinder roll by this object.

        See :class:`pathfinder.PathfinderRoll`.

        :param roll: The base roll to perform. Usually only a diespec.
        :type roll: str

        :param mods: Any modifiers to apply to the roll.
        :type mods: None or dict

        :param state: The roll expression state to begin with.
        :type state: None or dict

        :param vars: Any variables to inject into the roll expression.
        :type vars: dict

        :return: The roll result.
        :rtype: pathfinder.RollResult
        """
        state = state if state is not None else {}
        vars['__var'] = pathfinder.stats.resolve_roll_var
        state['stat object'] = self
        return pathfinder.RollResult(roll, mods, state, **vars)

    def d20_roll(self, mods=None, state=None, **vars):
        """
        Convenience method to perform a 1d20 roll.

        :rtype: pathfinder.RollResult
        """
        return self.pf_roll('1d20', mods=mods, state=state, **vars)

    @property
    def volume(self):
        """
        The volume of the object, based on its dimensions. If the object's
        dimensions yield zero volume, then a generalized volume based on the
        size category is used.

        :rtype: mudsling.utils.units._Quantity
        """
        vol = self.dimensions.volume
        if not vol:
            vol = pathfinder.sizes.volume(self.size_category)
        return vol

    _dependent_data = {
        'effects': {
            'process': '_process_effects',
            'start': lambda o: list(o._effects),
            'cache': '__effects'
        },
        'conditions': {
            'process': '_process_features',
            'start': lambda o: list(o._conditions),
            'cache': '__conditions'
        }
    }

    def _process_effects(self, effects, data):
        """
        Effects can provide a wide range of additional data, and this method
        may need to be overridden in child implementations to facilitate other
        data effects can handle for child types.
        """
        event = pathfinder.events.Event('conditions')
        event.conditions = []
        for effect in effects:
            effect.respond_to_event(event, None)
        data['conditions'].extend(event.conditions)

    def _process_features(self, features, data):
        """
        Features provide effects.
        """
        event = pathfinder.events.Event('permanent effects')
        event.effects = []
        for feature in [f for f in features if f is not None]:
            feature.respond_to_event(event, None)
        data['effects'].extend(event.effects)

    @property
    def features(self):
        return self.conditions

    @property
    def conditions(self):
        """:rtype: list of pathfinder.conditions.Condition"""
        if '__conditions' in self._stat_cache:
            return list(self._stat_cache['__conditions'])
        self._build_dependent_data()
        return self.conditions

    @property
    def effects(self):
        """:rtype: list of pathfinder.effects.Effect"""
        if '__effects' in self._stat_cache:
            return list(self._stat_cache['__effects'])
        self._build_dependent_data()
        return self.effects

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

    def trigger_event(self, event, **kw):
        event = super(PathfinderObject, self).trigger_event(event, **kw)
        self.expire_effects()
        if event.name in ('condition applied', 'condition removed',
                          'effect applied', 'effect removed'):
            self.clear_stat_cache()
        elif event.name == 'take damage':
            self._set_damage_conditions(event.prev_hp, event.prev_nl_damage)
        return event

    def get_stat_modifiers(self, stat, **params):
        """
        Get the modifiers for a stat.

        :param stat: The stat to modify.
        :type stat: str

        :param vs: Series of strings identifying what the stat is being
            evaluated against.
        :type vs: tuple or list

        :rtype: collections.OrderedDict
        """
        stat, tags = self.resolve_stat_name(stat)
        if 'vs' in params and isinstance(params['vs'], str):
            params['vs'] = (params['vs'],)
        event = self.trigger_event('stat mods', stat=stat, tags=tags,
                                   modifiers=OrderedDict(), **params)
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
        :type effect: pathfinder.effects.Effect or pathfinder.effects.Modifier
        """
        if isinstance(effect, pathfinder.modifiers.Modifier):
            effect = pathfinder.effects.Effect(effect, source)
        effect.apply_to(self.ref())

    def _apply_effect(self, effect):
        """
        :type effect: pathfinder.effects.Effect
        """
        if effect.expires:  # Only store expiring effects directly on object.
            self._check_attr('_effects', [])
            self._effects.append(effect)
        self.trigger_event('effect applied', effect=effect)

    def remove_effect(self, effect):
        self._check_attr('_effects', [])
        effects = self.effects
        if effect in effects:
            if effect in self._effects:
                self._effects.remove(effect)
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
        return self.remove_effects(
            e for e in self.effects if e.source == source)

    def expire_effects(self):
        """
        Evaluates all current effects to determine if they should expire.
        :return: List of expired effects.
        :rtype: list of pathfinder.effects.Effect
        """
        expired = []
        for effect in self._effects:  # All expirable effects are in _effects.
            if not effect.still_applies():
                expired.append(effect)
                self.remove_effect(effect)
        return expired

    def add_condition(self, condition, source=None):
        """Add the specified condition to the object directly, so that it is
        stored in the object's ._condition attribute.

        This also "applies" the condition.

        :param condition: The condition, condition class, or condition name
            specifying the condition to add to the object.
        :type condition: pathfinder.conditions.Condition or str or type

        :param source: The cause of the condition.
        :type source: any
        """
        if isinstance(condition, basestring):
            condition = pathfinder.data.get('condition', condition)
        if inspect.isclass(condition):
            condition = condition(source=source)
        if isinstance(condition, pathfinder.conditions.Condition):
            condition.apply_to(self)
            self._check_attr('_conditions', [])
            if condition not in self._conditions:
                self._conditions.append(condition)
        else:
            raise ValueError("Condition must be a string, condition class, or"
                             " condition instance")

    def remove_condition(self, condition):
        """Remove the specified condition.

        :param condition: The condition to remove.
        :type condition: pathfinder.conditions.Condition
        """
        condition.remove_from(self)
        if condition in self._conditions:
            self._conditions.remove(condition)

    def remove_conditions(self, condition=None, source=None):
        """Remove all conditions matching the specified criteria.

        :param condition: The condition type to remove. If None, remove all
            from the specified source.
        :param source: The source of the conditions to remove. If None, remove
            all conditions of the specified type.

        :returns: List of condition instances removed from object.
        :rtype: list of pathfinder.conditions.Condition
        """
        conditions = self.get_conditions(condition, source)
        for condition in conditions:
            self.remove_condition(condition)
        return conditions

    def get_conditions(self, condition=None, source=None):
        """Retrieve any instances of the condition specified.

        :param condition: The condition name or class to look for.
        :type condition: str or pathfinder.conditions.Condition subclass

        :param source: Limit results to those with a specified source.

        :return: List of conditions of the specified type which are currently
            in effect for this object.
        :rtype: list
        """
        if isinstance(condition, basestring):
            condition = pathfinder.data.get('condition', condition)
        return [c for c in self._conditions
                if (condition is None or c.__class__ == condition)
                and (source is None or source == c.source)]

    def has_condition(self, condition, source=None):
        """Determine whether or not the object has a specific condition.

        :param condition: The condition in question.
        :type condition: str or Condition subclass

        :return: Whether this object has the specified condition or not.
        :rtype: bool
        """
        return len(self.get_conditions(condition, source=source)) > 0

    def has_any_condition(self, conditions):
        for condition in conditions:
            if self.has_condition(condition):
                return True
        return False

    def _resist_or_reduct(self, type, damage_type):
        damage_types = pathfinder.damage.parse_damage_types(damage_type)
        options = []
        for damage_type in damage_types:
            event = self.trigger_event(type, damage_type=damage_type)
            applies = [v for v in event.responses.itervalues()
                       if v is not None]
            # Take the best resistance to a single damage type.
            if len(applies):
                options.append(max(applies))
        # If any of the damage ignores the resist/reduct, it all gets through.
        if len(options) < len(damage_types):
            return None
        # Use the least effective resist/reduct across multiple damage types.
        return min(options) if len(options) else None

    def damage_reduction(self, type):
        """
        Determine the damage reduction that applies to damage of a certain
        type.

        :param type: The damage type(s).
        :return: A tuple listing the modifier that grants the reduction and the
            value of that reduction.
        :rtype: int or None
        """
        return self._resist_or_reduct('damage reduction', type)

    def damage_resistance(self, type):
        """
        Determine the damage resistance that applies to damage of a certain
        type.

        :param type: The damage type(s).
        :return: A tuple listing the modifier that grants the resistance and
            the value of that resistance.
        :rtype: int or None
        """
        return self._resist_or_reduct('damage resistance', type)

    def take_damage(self, damages):
        """
        Deal damage to the object.

        :param damages: The damages inflicted to the object.
        :type damages: (list or tuple or set) of pathfinder.damage.Damage
        """
        if isinstance(damages, int):
            damages = (pathfinder.damage.Damage(damages),)
        elif isinstance(damages, pathfinder.damage.Damage):
            damages = (damages,)
        for dmg in damages:
            self._take_damage(dmg)

    def _take_damage(self, damage):
        """
        Low-level method to inflict damage. Should only be called by
        take_damage().

        :param damage: The damage being inflicted.
        :type damage: pathfinder.damage.Damage
        """
        # todo: Half damage to objects via energy/ranged?
        # Reduction.
        reduction = self.damage_reduction(damage.types) or 0
        resistance = self.damage_resistance(damage.types) or 0
        points = damage.points - reduction - resistance
        # Hardness reduces physical damage.
        if len([dt for dt in damage.types if dt.kind != 'physical']) == 0:
            points -= self.hardness
        prev_hp = self.remaining_hp
        prev_nl_damage = self.nonlethal_damage
        trigger_event = False
        if damage.nonlethal:
            if not self.nonlethal_immunity:
                if self.nonlethal_damage >= self.max_hp:
                    # Nonlethal damage is lethal after a point.
                    self.damage += points
                else:
                    self.nonlethal_damage += points
                trigger_event = True
        else:
            self.damage += points
            trigger_event = True
        if trigger_event:
            self.trigger_event('take damage', damage=damage, prev_hp=prev_hp,
                               prev_nl_damage=prev_nl_damage)

    def _set_damage_conditions(self, prev_hp, prev_nl_damage):
        """
        Set various conditions based on current hit points as well as their
        previous values.

        :param prev_hp: Previous hit points.
        :param prev_nl_damage: Previous nonlethal damage.
        """
        if self.remaining_hp <= 0 and not self.has_condition('broken'):
            self.add_condition('broken', source='damage')
