import math
from collections import OrderedDict

from mudsling.objects import Object

from mudslingcore.objects import Thing as CoreThing
from mudslingcore.objects import Character as CoreCharacter

import dice
import pathfinder

from .stats import HasStats
from .events import Event
from .features import HasFeatures
from .sizes import SizeCategory
from .modifiers import Modifier
from .effects import Effect


class StatModEvent(Event):
    def __init__(self, *a, **kw):
        super(StatModEvent, self).__init__(*a, **kw)
        self.modifiers = OrderedDict()


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
        event = StatModEvent(stat, **kw)
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
        if 'effects' not in self.__dict__:
            self.effects = []
        self.effects.append(effect)

    def take_damage(self, damage):
        pass


class Thing(CoreThing, PathfinderObject):
    """
    Basic game world object that can interact with Pathfinder features.
    """


class Character(CoreCharacter, PathfinderObject):
    """
    A Pathfinder-enabled character/creature/etc.
    """
    feats = []
    skills = {}
    stat_defaults = {
        'Strength': 0,     'STR': 0,
        'Dexterity': 0,    'DEX': 0,
        'Constitution': 0, 'CON': 0,
        'Wisdom': 0,       'WIS': 0,
        'Intelligence': 0, 'INT': 0,
        'Charisma': 0,     'CHA': 0
    }

    def add_feat(self, feat_class, subtype=None):
        if 'feats' not in self.__dict__:
            self.feats = []
        feat = feat_class(subtype)
        feat.apply_static_effects(self)
        self.feats.append(feat)

    def add_skill_rank(self, skill, ranks=1):
        if 'skills' not in self.__dict__:
            self.skills = {}
        if skill in self.skills:
            self.skills[skill] += ranks
        else:
            self.skills[skill] = ranks

    def skill_rank(self, skill):
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        return self.skills.get(skill, 0)

    def get_all_stat_names(self):
        names = super(Character, self).get_all_stat_names()
        names.update(pathfinder.abilities)
        names.update(pathfinder.abil_short)
        names.update(pathfinder.data.names('skill'))
        return names

    def get_stat_default(self, stat):
        # Catch skill names to give the 0 default.
        if stat in pathfinder.data.registry['skill']:
            return 0
        else:
            return super(Character, self).get_stat_default(stat)

    def get_stat_base(self, stat):
        if stat in pathfinder.abil_short:
            abil = pathfinder.abilities[pathfinder.abil_short.index(stat)]
            return math.trunc(self.get_stat(abil) / 2)
        elif stat in pathfinder.data.registry['skill']:
            return self.skill_rank(stat)
        else:
            return super(Character, self).get_stat_base(stat)
