from collections import namedtuple

from .features import CharacterFeature
from .data import ForceSlotsMetaclass
from pathfinder.characters import is_pfchar
from .feats import Feat


Level = namedtuple('Level', 'level bab fort ref will features')


def lvl(level, bab, fort, ref, will, *features):
    return Level(level, bab, fort, ref, will, features)


class Class(CharacterFeature):
    __metaclass__ = ForceSlotsMetaclass
    name = ''
    hit_die = 'd1'
    skills = ()
    skill_points = '0 + INT'
    levels = []


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
    modifiers = ['+1 to Will saves against fear']


class ArmorTraining(CharacterFeature):
    name = 'Armor Training'
    description = "The fighter learns to be more maneuverable in armor."
    modifiers = [
        "+1 to armor check penalty reduction",
        "+1 to armor dex limit"
    ]


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


class Fighter(Class):
    name = 'Fighter'
    hit_die = 'd10'
    skills = ('Climb', 'Craft (armor)', 'Craft (bows)', 'Craft (carpentry)',
              'Craft (glass)', 'Craft (leather)', 'Craft (sculptures)',
              'Craft (ships)', 'Craft (stonemasonry)', 'Craft (weapons)',
              'Handle Animal', 'Intimidate', 'Knowledge (dungeoneering)',
              'Knowledge (engineering)', 'Profession', 'Ride', 'Survival',
              'Swim')
    skill_points = '2 + INT'
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
    ]
