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
