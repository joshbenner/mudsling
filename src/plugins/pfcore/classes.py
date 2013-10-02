from mudsling.utils.sequence import CaselessDict

from pathfinder.classes import Class, lvl, GainFeat, BonusFeat
from pathfinder.feats import Feat
from pathfinder.characters import CharacterFeature, is_pfchar
from pathfinder.modifiers import modifiers


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
    def subtypes(cls):
        groups = sorted(weapon_training_groups.keys())
        return CaselessDict(zip(groups, groups))

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