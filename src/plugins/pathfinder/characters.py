import math
import re

from mudslingcore.objects import Character as CoreCharacter

from dice import Roll
from mudsling.storage import ObjRef
from mudsling.commands import all_commands

import pathfinder
import pathfinder.prerequisites
from .feats import parse_feat
from .objects import PathfinderObject
from .events import Event
from .races import Race


class Character(CoreCharacter, PathfinderObject):
    """
    A Pathfinder-enabled character/creature/etc.
    """
    from .commands import character as character_commands
    private_commands = all_commands(character_commands)
    del character_commands

    finalized = False
    race = None
    levels = []
    feats = []
    skills = {}
    ability_points = 0
    skill_points = 0
    feat_slots = {}  # key = type or '*', value = how many
    languages = []
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
        features = []
        if self.race is not None:
            features.append(self.race)
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

    def set_race(self, race):
        if self.race is not None and issubclass(self.race, Race):
            self.race.remove_from(self)
        self.race = race
        race.apply_to(self)

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

    def remove_feat_slot(self, type='*', slots=1):
        self._check_attr('feat_slots', {})
        if type in self.feat_slots:
            if slots >= self.feat_slots[type]:
                del self.feat_slots[type]
            else:
                self.feat_slots[type] -= slots

    def get_feat(self, feat, subtype=None):
        if isinstance(feat, basestring):
            feat, subtype_ = parse_feat(feat)
            if subtype is None and subtype_ is not None:
                subtype = subtype_
        for f in self.feats:
            if f.__class__ == feat and f.subtype == subtype:
                return f
        return None

    def has_feat(self, feat, subtype=None):
        return self.get_feat(feat, subtype) is not None

    def has_feature(self, name, subtype=None):
        name = name.lower()
        for feature in self.features:
            if feature.name.lower() == name:
                if hasattr(feature, 'subtype'):
                    if feature.subtype == subtype:
                        return True
                elif subtype is None:
                    return True
        return False

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
            return math.trunc(self.get_stat(abil) / 2 - 5)
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

    def check_prerequisites(self, prerequisites):
        return pathfinder.prerequisites.check(prerequisites, self)

    def spoken_languages(self):
        e = Event('spoken languages')
        e.languages = []
        self.trigger_event(e)
        return e.languages


def is_pfchar(obj):
    return (isinstance(obj, Character)
            or (isinstance(obj, ObjRef) and obj.isa(Character)))
