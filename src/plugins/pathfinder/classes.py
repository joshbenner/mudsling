from collections import namedtuple

from mudsling.storage import ObjRef

from .features import Feature
from .data import ForceSlotsMetaclass
from .objects import is_pfobj


lvl = namedtuple('lvl', 'level bab fort ref will features')


class Class(Feature):
    __metaclass__ = ForceSlotsMetaclass
    name = ''
    hit_die = 'd1'
    skills = ()
    skill_points = '0 + INT'
    levels = []


class AbilityPoint(Feature):
    name = "Ability Point"
    description = "Increase an ability by one point."
    persistent = False

    def apply_to(self, obj):
        if is_pfobj(obj):
            obj.ability_points += 1


class GainFeat(Feature):
    name = "Feat"
    description = "Gain a feat."
    persistent = False

    def apply_to(self, obj):
        if is_pfobj(obj):
            obj.add_feat_slot()


class BonusFeat(Feature):
    """
    Grants a bonus feat.
    """
    name = 'Bonus Feat'
    description = "Gain a bonus combat feat."
    persistent = False

    def apply_to(self, obj):
        if is_pfobj(obj):
            obj.add_feat_slot(type='combat')


class Bravery(Feature):
    name = 'Bravery'
    description = "+1 to will saves vs fear; +1 every 4th level after 2nd."
    modifiers = ['+trunc((LVL + 2) / 4) to Will saves against fear']


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
