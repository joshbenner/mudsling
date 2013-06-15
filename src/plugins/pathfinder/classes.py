from collections import namedtuple

from .features import CharacterFeature
from .data import ForceSlotsMetaclass
from pathfinder.characters import is_pfchar


lvl = namedtuple('lvl', 'level bab fort ref will features')


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
    modifiers = ['+trunc((LVL + 2) / 4) to Will saves against fear']


class ArmorTraining(CharacterFeature):
    name = 'Armor Training'
    description = "The fighter learns to be more maneuverable in armor."
    modifiers = [
        "+min(4, trunc((level + 1) / 4)) to armor check penalty reduction",
        "+min(4, trunc((level + 1) / 4)) to armor dex limit"
    ]


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
        lvl(1, 1, 2, 0, 0, (GainFeat, BonusFeat,)),
        lvl(2, 2, 3, 0, 0, (BonusFeat,))
    ]
