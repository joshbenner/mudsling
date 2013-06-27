from collections import namedtuple

from .features import CharacterFeature
from .modifiers import modifiers
from pathfinder.characters import is_pfchar
from .feats import Feat


Level = namedtuple('Level', 'level bab fort ref will special')


def lvl(level, bab, fort, ref, will, *special):
    return Level(level, bab, fort, ref, will, special)


class Class(CharacterFeature):
    name = ''
    hit_die = 'd1'
    skills = ()
    skill_points = '0'
    levels = []

    @classmethod
    def apply_level(cls, level, char):
        """
        @type char: L{pathfinder.characters.Character}
        """
        next_lvl = cls.levels[level - 1]
        for special in next_lvl.special:
            char.add_feature(special)
        cls.add_hitpoints(char)
        cls.add_skill_points(char)

    @classmethod
    def add_hitpoints(cls, char):
        if char.level == 1:
            min_, max_ = char.roll_limits(cls.hit_die)
            char.hitpoints = max_ + max(0, char.con_mod)
            char.tell('You begin with {y', char.hitpoints, '{g hit {npoints.')
        else:
            hp_to_add, desc = char.roll(cls.hit_die, desc=True)
            char.hitpoints += hp_to_add + max(0, char.con_mod)
            char.hp_increases.append((desc, hp_to_add))
            char.tell('You gain {y', hp_to_add, '{g hit{n points!')

    @classmethod
    def add_skill_points(cls, char):
        points = max(1, char.roll(cls.skill_points))
        char.skill_points += points
        char.tell('You gain {y', points, '{m skill{n points!')


class GainFeat(CharacterFeature):
    name = "Feat"
    description = "Gain a feat."
    feat_type = '*'

    def apply_to(self, obj):
        if is_pfchar(obj):
            obj.add_feat_slot(type=self.feat_type)

    def remove_from(self, obj):
        if is_pfchar(obj):
            obj.remove_feat_slot(type=self.feat_type)


class BonusFeat(GainFeat):
    """
    Grants a bonus feat.
    """
    name = 'Bonus Feat'
    description = "Gain a bonus combat feat."
    feat_type = 'combat'


class Bravery(CharacterFeature):
    name = 'Bravery'
    description = "+1 to will saves vs fear; +1 every 4th level after 2nd."
    modifiers = modifiers('+1 to Will saves against fear')


class ArmorTraining(CharacterFeature):
    name = 'Armor Training'
    description = "The fighter learns to be more maneuverable in armor."
    modifiers = modifiers(
        "+1 to armor check penalty reduction",
        "+1 to armor dex limit"
    )


class WeaponTrainingSlot(GainFeat):
    name = 'Weapon Training'
    description = "The fighter is highly trained in a chosen group of weapons."
    feat_type = 'weapon training'


weapon_training_groups = {
    'Axes': [],
    'Blades, Heavy': [],
    # todo: fill out this mapping
}


class WeaponTraining(Feat):
    __slots__ = ('gained_at_level',)
    name = 'Weapon Training'
    type = 'weapon training'
    restricted = True
    multiple = True
    _prerequisites = ['weapon training feat slot']

    @classmethod
    def subtypes(cls, character=None):
        return sorted(weapon_training_groups.keys())

    def apply_to(self, obj):
        if is_pfchar(obj):
            self.gained_at_level = obj.get_stat('level')

    def respond_to_event(self, event, responses):
        # todo: Implement weapon bonuses
        pass


class ArmorMastery(CharacterFeature):
    name = 'Armor Mastery'
    description = "The fighter's use of armor and shields is so finely honed "\
                  "that he effectively disregards 5 points of any blow."

    def respond_to_event(self, event, responses):
        if event.name == "damage reduction":
            # todo: Provide DR 5/- if wearing armor or wielding a shield.
            pass


class WeaponMastery(CharacterFeature):
    name = 'Weapon Mastery'
    description = "A fighter's chosen weapon confirms all critical hits, and "\
                  "deals more critical damage than usual."
    # todo: Implement?


class Fighter(Class):
    name = 'Fighter'
    hit_die = 'd10'
    skills = ('Climb', 'Craft (armor)', 'Craft (bows)', 'Craft (carpentry)',
              'Craft (glass)', 'Craft (leather)', 'Craft (sculptures)',
              'Craft (ships)', 'Craft (stonemasonry)', 'Craft (weapons)',
              'Handle Animal', 'Intimidate', 'Knowledge (dungeoneering)',
              'Knowledge (engineering)', 'Profession', 'Ride', 'Survival',
              'Swim')
    skill_points = '2 + INT mod'
    levels = [
        #  LVL BAB Fort Ref Will Special
        lvl(1,  1,  2,   0,  0,  GainFeat, BonusFeat),
        lvl(2,  2,  3,   0,  0,  BonusFeat, Bravery),
        lvl(3,  3,  3,   1,  1,  GainFeat, ArmorTraining),
        lvl(4,  4,  4,   1,  1,  BonusFeat),
        lvl(5,  5,  4,   1,  1,  GainFeat, WeaponTrainingSlot),
        lvl(6,  6,  5,   2,  2,  BonusFeat, Bravery),
        lvl(7,  7,  5,   2,  2,  GainFeat, ArmorTraining),
        lvl(8,  8,  6,   2,  2,  BonusFeat),
        lvl(9,  9,  6,   3,  3,  GainFeat, WeaponTrainingSlot),
        lvl(10, 10, 7,   3,  3,  BonusFeat, Bravery),
        lvl(11, 11, 7,   3,  3,  GainFeat, ArmorTraining),
        lvl(12, 12, 8,   4,  4,  BonusFeat),
        lvl(13, 13, 8,   4,  4,  GainFeat, WeaponTrainingSlot),
        lvl(14, 14, 9,   4,  4,  BonusFeat, Bravery),
        lvl(15, 15, 9,   5,  5,  GainFeat, ArmorTraining),
        lvl(16, 16, 10,  5,  5,  BonusFeat),
        lvl(17, 17, 10,  5,  5,  GainFeat, WeaponTrainingSlot),
        lvl(18, 18, 11,  6,  6,  BonusFeat),
        lvl(19, 19, 11,  6,  6,  GainFeat, ArmorMastery),
        lvl(20, 20, 12,  6,  6,  BonusFeat, WeaponMastery)
    ]
