import re
import math
from collections import OrderedDict

from mudsling.objects import Object
from mudsling.storage import ObjRef

from mudslingcore.objects import Thing as CoreThing
from mudslingcore.objects import Character as CoreCharacter

from dice import Roll
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
        self._check_attr('effects', [])
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
    levels = []
    feats = []
    skills = {}
    ability_points = 0
    skill_points = 0
    feat_slots = {}  # key = type or '*', value = how many
    stat_defaults = {
        'strength': 0,     'str': 0,
        'dexterity': 0,    'dex': 0,
        'constitution': 0, 'con': 0,
        'wisdom': 0,       'wis': 0,
        'intelligence': 0, 'int': 0,
        'charisma': 0,     'cha': 0,
        'str modifier': Roll('str'), 'str mod': Roll('str'),
        'dex modifier': Roll('dex'), 'dex mod': Roll('dex'),
        'con modifier': Roll('con'), 'con mod': Roll('con'),
        'wis modifier': Roll('wis'), 'wis mod': Roll('wis'),
        'int modifier': Roll('int'), 'int mod': Roll('int'),
        'cha modifier': Roll('cha'), 'cha mod': Roll('cha'),

        'level': 0,
        'lvl': Roll('level'),
        'hit dice': Roll('level'),
        'hd': Roll('hit dice'),

        'initiative': Roll('DEX'),
        'initiative check': Roll('1d20 + initiative'),
        'shield bonus': 0,
        'armor bonus': 0,
        'armor enhancement bonus': 0,
        'range increment modifier': -2,
        'shoot into melee modifier': -4,
        'improvised weapon modifier': -4,
        'two weapon primary hand modifier': -4,
        'two weapon off hand modifier': -8,
        'melee damage modifier': Roll('STR'),
        'primary melee damage bonus': Roll('melee damage modifier'),
        'off hand melee damage bonus': Roll('trunc(melee damage modifier / 2)')
    }

    # These are used to resolve stats to their canonical form.
    _skill_check_re = re.compile('(.*)(?: +(check|roll)s?)?', re.I)
    _save_re = re.compile(
        '(Fort(?:itude)?|Ref(?:lex)?|Will)( +(save|check)s?)?', re.I)

    # Used to identify class level stats for isolating base stat value.
    _class_lvl_re = re.compile('(.*) +levels?', re.I)

    @property
    def features(self):
        features = [self.race]
        features.extend(c for c in self.classes.iterkeys())
        features.extend(self.feats)
        return features

    @property
    def classes(self):
        classes = {}
        for lvl in self.levels:
            if lvl not in classes:
                classes[lvl] = 1
            else:
                classes[lvl] += 1
        return classes

    def add_class(self, class_):
        self._check_attr('levels', [])
        self.levels.append(class_)

    def add_feat(self, feat_class, subtype=None):
        self._check_attr('feats', [])
        feat = feat_class(subtype)
        feat.apply_static_effects(self)
        self.feats.append(feat)

    def add_feat_slot(self, type='*', slots=1):
        self._check_attr('feat_slots', {})
        if type not in self.feat_slots:
            self.feat_slots[type] += slots
        else:
            self.feat_slots[type] = slots

    def add_skill_rank(self, skill, ranks=1):
        self._check_attr('skills', {})
        if skill in self.skills:
            self.skills[skill] += ranks
        else:
            self.skills[skill] = ranks

    def skill_rank(self, skill):
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        return self.skills.get(skill, 0)

    def resolve_stat_name(self, name):
        name = name.lower()
        m = self._save_re.match(name)
        if m:
            name = self.resolve_stat_name(m.groups()[0])
        if name == 'fort':
            return 'fortitude'
        elif name == 'ref':
            return 'reflex'
        elif name == 'will':
            return 'will'
        m = self._skill_check_re.match(name)
        if m:
            name, extra = m.groups()
            return name, ('check',) if extra else ()
        return super(PathfinderObject, self).resolve_stat_name(name)

    def get_all_stat_names(self):
        names = super(Character, self).get_all_stat_names()
        names.update(pathfinder.abilities)
        names.update(pathfinder.abil_short)
        names.update(pathfinder.data.names('skill'))
        return names

    def get_stat_default(self, stat):
        # Catch skill names to give the 0 default. We don't define defaults on
        # the character class since these could change, and we don't want to
        # update two places to change a skill. Also, skills may not be loaded
        # into registry at class definition time.
        if stat in pathfinder.data.registry['skill']:
            return 0
        else:
            return super(Character, self).get_stat_default(stat)

    def get_stat_base(self, stat):
        stat = stat.lower()
        if stat == 'level' or stat == 'hit dice':
            return len(self.levels)
        if stat in pathfinder.abil_short:
            abil = pathfinder.abilities[pathfinder.abil_short.index(stat)]
            return math.trunc(self.get_stat(abil) / 2)
        elif stat in pathfinder.data.registry['skill']:
            return self.skill_rank(stat)
        else:
            m = self._class_lvl_re.match(stat)
            if m:
                class_name = m.groups()[0].lower()
                for cls, levels in self.classes.iteritems():
                    if cls.name.lower == class_name:
                        return levels
                return 0
            return super(Character, self).get_stat_base(stat)
