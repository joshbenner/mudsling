"""
Miscellaneous special abilities. Special abilities are much like feats, but
they generally cannot be gained by using a feat slot. Usually, special
abilities are a trait of the race, class, etc.
"""

from .feats import Feat


class SpecialAbility(Feat):
    feature_type = 'special ability'

    @classmethod
    def prerequisites(cls, subtype=None):
        # Special abilities cannot be gained like other feats.
        return ['restricted']

    def __repr__(self):
        return 'Special Ability: %s' % str(self)


class Darkvision(SpecialAbility):
    name = 'Darkvision'
    description = "Extraordinary ability to see with no light source at all."


class LowLightVision(SpecialAbility):
    name = "Low-Light Vision"
    description = "Extraordinary ability to see well in even dim light."


class Scent(SpecialAbility):
    name = "Scent"
    description = "Extraordinary ability to detect creatures by their scent."
