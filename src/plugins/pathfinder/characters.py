import math
import re

from mudslingcore.objects import Character as CoreCharacter

from dice import Roll
from mudsling.storage import ObjRef
from mudsling.commands import all_commands
from mudsling import errors

import pathfinder
import pathfinder.prerequisites
from .feats import parse_feat
from .objects import PathfinderObject
from .events import Event
from .races import Race
from .advancement import active_table
import pathfinder.errors as pferr


class Character(CoreCharacter, PathfinderObject):
    """
    A Pathfinder-enabled character/creature/etc.
    """

    finalized = False
    xp = 0
    race = None
    levels = []
    ability_increases = []
    hp_increases = []
    favored_class_bonuses = []
    feats = []
    skills = {}
    skill_points = 0
    level_up_skills = {}
    feat_slots = {}  # key = type or '*', value = how many
    languages = []
    _abil_modifier_stats = (
        'strength modifier',
        'dexterity modifier',
        'constitution modifier',
        'wisdom modifier',
        'intelligence modifier',
        'charisma modifier'
    )
    stat_defaults = {
        'strength': 0,     'str': Roll('strength'),
        'dexterity': 0,    'dex': Roll('dexterity'),
        'constitution': 0, 'con': Roll('constitution'),
        'wisdom': 0,       'wis': Roll('wisdom'),
        'intelligence': 0, 'int': Roll('intelligence'),
        'charisma': 0,     'cha': Roll('charisma'),
        'str mod': Roll('strength modifier'),
        'dex mod': Roll('dexterity modifier'),
        'con mod': Roll('constitution modifier'),
        'wis mod': Roll('wisdom modifier'),
        'int mod': Roll('intelligence modifier'),
        'cha mod': Roll('charisma modifier'),

        'level': 0,
        'lvl': Roll('level'),
        'hit dice': Roll('level'),
        'hd': Roll('hit dice'),

        'initiative': Roll('dexterity modifier'),
        'initiative check': Roll('1d20 + initiative'),
        'shield bonus': 0,
        'armor bonus': 0,
        'armor enhancement bonus': 0,
        'range increment modifier': -2,
        'shoot into melee modifier': -4,
        'improvised weapon modifier': -4,
        'two weapon primary hand modifier': -4,
        'two weapon off hand modifier': -8,
        'melee damage modifier': Roll('strength modifier'),
        'primary melee damage bonus': Roll('melee damage modifier'),
        'off hand melee damage bonus': Roll('trunc(melee damage modifier / 2)')
    }
    # Map attributes to stats.
    stat_attributes = {
        'level': 'level',
        'strength': 'strength',
        'constitution': 'constitution',
        'dexterity': 'dexterity',
        'wisdom': 'wisdom',
        'intelligence': 'intelligence',
        'charisma': 'charisma',
        'str': 'strength', 'con': 'constitution', 'dex': 'dexterity',
        'wis': 'wisdom', 'int': 'intelligence', 'cha': 'charisma',
        'strength_mod': 'strength modifier',
        'constitution_mod': 'constitution modifier',
        'dexterity_mod': 'dexterity modifier',
        'wisdom_mod': 'wisdom modifier',
        'intelligence_mod': 'intelligence modifier',
        'charisma_mod': 'charisma modifier',
        'str_mod': 'strength modifier',
        'con_mod': 'constitution modifier',
        'dex_mod': 'dexterity modifier',
        'wis_mod': 'wisdom modifier',
        'int_mod': 'intelligence modifier',
        'cha_mod': 'charisma modifier',
    }

    # These are used to resolve stats to their canonical form.
    _skill_check_re = re.compile('(.*)(?: +(check|roll)s?)', re.I)
    _save_re = re.compile(
        '(Fort(?:itude)?|Ref(?:lex)?|Will)( +(save|check)s?)', re.I)

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

    @property
    def favored_classes(self):
        return (self.levels[0],) if self.levels else ()

    @property
    def unused_favored_class_bonuses(self):
        """
        Return the number of unused favored class bonuses.
        @rtype: C{int}
        """
        bonuses = 0
        favored = self.favored_classes
        for cls in self.levels:
            if cls in favored:
                bonuses += 1
        return bonuses - len(self.favored_class_bonuses)

    def add_xp(self, xp, stealth=False):
        before = self.current_xp_level
        if xp > 0:
            self.xp += xp
            if not stealth:
                self.tell("{gYou gained {c", xp, "{g experience points!")
                if before < self.current_xp_level:
                    self.tell('{r*** {yYOU CAN LEVEL-UP! {r***')

    @property
    def current_xp_level(self):
        lvl = 0
        for xp in active_table():
            if self.xp >= xp:
                lvl += 1
            else:
                break
        return lvl

    @property
    def next_level_xp(self):
        current_lvl = self.current_xp_level
        table = active_table()
        if len(table) >= current_lvl:
            return table[current_lvl]
        else:
            return None

    @property
    def xp_to_next_level(self):
        return self.next_level_xp - self.xp

    def increase_ability(self, ability):
        self._check_attr('ability_increases', [])
        self.ability_increases.append(ability)
        previous = self.get_stat(ability)
        new = previous + 1
        self.set_stat(ability, new)
        a = ability.capitalize()
        self.tell('{gYour {m', a, '{g score is now {c', new, '{g.')

    def increment_stat(self, stat, amount=1):
        existing = self.get_stat(stat)
        self.set_stat(stat, existing + amount)

    def set_race(self, race):
        if self.race is not None and issubclass(self.race, Race):
            self.race.remove_from(self)
        self.race = race
        if race is not None:
            race.apply_to(self)
        self.clear_stat_cache()

    def add_class(self, class_):
        self._check_attr('levels', [])
        self._check_attr('hp_increases', [])
        self.levels.append(class_)
        class_.apply_level(self.classes[class_], self)
        self.clear_stat_cache()
        self.tell('{gYou have gained a level of {m', class_.name, '{g.')

    def class_skills(self):
        if '__class_skills' in self._stat_cache:
            return self._stat_cache['__class_skills']
        skills = []
        for class_ in self.classes.iterkeys():
            for skill_name in class_.skills:
                try:
                    skill = pathfinder.data.match(skill_name, types=('skill',))
                except errors.MatchError:
                    # Exclude broken skill name.
                    continue
                if skills not in skills:
                    skills.append(skill)
        self._check_attr('_stat_cache', {})
        self._stat_cache['__class_skills'] = skills
        return skills

    def add_feat(self, feat_class, subtype=None, source=None, slot=None):
        self._check_attr('feats', [])
        if source is 'slot' and slot is None:
            compatible = self.compatible_feat_slots(feat_class, subtype)
            if compatible:
                slot = compatible[0]
            else:
                msg = "No feat slot available for %s" % feat_class.name
                raise pferr.CharacterError(msg)
        existing = self.get_feat(feat_class, subtype)
        if existing is not None:
            if source == 'slot' and 'slot' in existing.sources:
                msg = "Feat can only occupy one feat slot."
                raise pferr.CharacterError(msg)
            existing.sources.append(source)
        else:
            feat = feat_class(subtype, source, slot)
            feat.apply_to(self)
            self.feats.append(feat)
            self.clear_stat_cache()

    def remove_feat(self, feat, source=None):
        """
        Remove a feat instance from a character. If the feat is provided by
        multiple sources, it may not actually be removed.

        @param feat: The feat INSTANCE to remove.
        @type feat: L{pathfinder.feats.Feat}
        @param source: The source to remove in the case of a multi-source feat.
            If a non-None source is specified but is not in the feat's list of
            sources, then the feat will not be removed. If no source is given,
            and the feat is occupying a feat slot, the slot will be vacated.
        """
        if source is not None:
            if source in feat.sources:
                feat.sources.remove(source)
                if source == 'slot':
                    feat.slot = None
            else:
                # Specified source does not provide the feat.
                return
        if feat.sources:  # Something still keeping feat around. Abort!
            return
        # Remove the feat that is no longer provided by anything.
        self.feats.remove(feat)
        feat.remove_from(self)
        self.clear_stat_cache()

    def add_feat_slot(self, type='general', slots=1):
        self._check_attr('feat_slots', {})
        if type not in self.feat_slots:
            self.feat_slots[type] = slots
        else:
            self.feat_slots[type] += slots

    def remove_feat_slot(self, type='general', slots=1):
        self._check_attr('feat_slots', {})
        if type in self.feat_slots:
            if slots >= self.feat_slots[type]:
                del self.feat_slots[type]
            else:
                self.feat_slots[type] -= slots

    def feats_by_slot(self):
        slots = {}
        for slot_type in self.feat_slots.iterkeys():
            slots[slot_type] = []
        for feat in self.feats:
            if feat.slot is not None:
                if feat.slot not in slots:
                    slots[feat.slot] = []
                slots[feat.slot].append(feat)
        return slots

    def available_feat_slots(self):
        existing = self.feats_by_slot()
        available = {}
        for slot_type, count in self.feat_slots.iteritems():
            available[slot_type] = count - len(existing[slot_type])
        return available

    def compatible_feat_slots(self, feat_class, subtype=None):
        return [st for st, c in self.available_feat_slots()
                if c > 0 and st in feat_class.compatible_slots(subtype)]

    def get_feat(self, feat, subtype=None):
        """
        Return the feat instance if this character has the specified feat.

        If '*' is passed for subtype, then first feat of the feat class found
        will be returned. Useful for determining if character has a feat with
        any subtype.

        @param feat: The feat class or name of the feat.
        @param subtype: The subtype. Overrides subtype in feat name.
        """
        if isinstance(feat, basestring):
            feat, subtype_ = parse_feat(feat)
            if subtype is None and subtype_ is not None:
                subtype = subtype_
        for f in self.feats:
            if f.__class__ == feat and (f.subtype == subtype
                                        or subtype == '*'):
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

    def add_skill_rank(self, skill, ranks=1, level_up=True,
                       deduct_points=True):
        self._check_attr('skills', {})
        self._check_attr('level_up_skills', {})
        skill_current = self.skills.get(skill, 0)
        if skill_current >= self.level:
            raise pferr.SkillError("Cannot train skills above your level.")
        if deduct_points:
            if self.skill_points < ranks:
                raise pferr.SkillError("Insufficient skill points.")
            self.skill_points -= ranks
        self.skills[skill] = skill_current + ranks
        if level_up:
            lvlup_current = self.level_up_skills.get(skill, 0)
            self.level_up_skills[skill] = lvlup_current + ranks
        self.clear_stat_cache()
        self.tell('You are now trained to rank {g', skill_current + ranks,
                  '{n in {c', skill, '{n (effective check bonus: {y',
                  pathfinder.format_modifier(self.skill_base_bonus(skill)),
                  '{n).')

    def remove_skill_rank(self, skill, ranks=1, level_up=True,
                          credit_points=True):
        self._check_attr('skills', {})
        self._check_attr('level_up_skills', {})
        skill_current = self.skills.get(skill, 0)
        if skill_current < ranks:
            raise pferr.SkillError("No ranks of %s to remove." % skill.name)
        if level_up:
            lvlup_current = self.level_up_skills.get(skill, 0)
            if lvlup_current < ranks:
                msg = "Cannot remove skill ranks gained in a previous level."
                raise pferr.SkillError(msg)
            self.level_up_skills[skill] = lvlup_current - ranks
        if credit_points:
            self.skill_points += ranks
        self.skills[skill] -= ranks
        self.clear_stat_cache()
        self.tell('You are now trained to rank {g', skill_current - ranks,
                  '{n in {c', skill, '{n (effective check bonus: {y',
                  pathfinder.format_modifier(self.skill_base_bonus(skill)),
                  '{n).')

    def skill_ranks(self, skill):
        """
        How many ranks of training does the character have in the skill?
        """
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        return self.skills.get(skill, 0)

    def skill_base_bonus(self, skill):
        """
        Get the base skill bonus. Does not include effects.

        Base bonus = ranks + ability modifier + class skill bonus (if any)
        """
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        trained = self.skill_ranks(skill)
        ability_modifier = self.get_stat(skill.ability + ' mod')
        bonus = 3 if trained and skill in self.class_skills() else 0
        return trained + ability_modifier + bonus

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
        stat = self.resolve_stat_name(stat)[0]
        if stat in pathfinder.data.registry['skill']:
            return 0
        else:
            return super(Character, self).get_stat_default(stat)

    def get_stat_base(self, stat):
        stat = self.resolve_stat_name(stat)[0]
        if stat == 'level' or stat == 'hit dice':
            return len(self.levels)
        if stat in self._abil_modifier_stats:
            return math.trunc(self.get_stat(stat.split(' ')[0]) / 2 - 5)
        elif stat in pathfinder.data.registry['skill']:
            return self.skill_base_bonus(stat)
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

# Assign commands here to avoid circular import issues.
from .commands import character as character_commands
Character.private_commands = all_commands(character_commands)
del character_commands


def is_pfchar(obj):
    return (isinstance(obj, Character)
            or (isinstance(obj, ObjRef) and obj.isa(Character)))
