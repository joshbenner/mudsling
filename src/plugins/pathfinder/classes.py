from collections import namedtuple

from .characters import is_pfchar, CharacterFeature


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
            feature = char.add_feature(special)
            char.level_log(level, 'class_special', cls, feature)

        # Hit points.
        if level == 1:
            min_, points = char.roll_limits(cls.hit_die)
        else:
            points = cls.hit_die
        points = char.gain_hitpoints(points)
        char.level_log(level, 'hitpoints', cls, points)

        # Skill points.
        points = max(1, char.roll(cls.skill_points))
        char.gain_skill_points(points)
        char.level_log(level, 'skillpoints', cls, points)

    @classmethod
    def undo_level_class_special(cls, char, level, feature):
        char.remove_feature(feature)

    @classmethod
    def undo_level_hitpoints(cls, char, level, points):
        char.lose_hitpoints(points)

    @classmethod
    def undo_level_skillpoints(cls, char, level, points):
        char.lose_skill_points(points)


class GainFeat(CharacterFeature):
    name = "Feat"
    description = "Gain a feat."
    feat_type = 'general'

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


