import inspect

import pathfinder.characters
import pathfinder.features
import pathfinder.events


class Level(object):
    def __init__(self, level, bab, fort, ref, will, *special):
        self.level = level
        self.bab = bab
        self.fort = fort
        self.ref = ref
        self.will = will
        self.special = special


class Class(pathfinder.features.StaticFeature):
    feature_type = 'class'

    name = ''
    hit_die = 'd1'
    skills = ()
    skill_points = '0'

    #: :type: list of pathfinder.classes.Level
    levels = []

    @classmethod
    def apply_level(cls, level, char):
        """
        :type char: pathfinder.characters.Character
        """
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
    def undo_level_hitpoints(cls, char, level, points):
        char.lose_hitpoints(points)

    @classmethod
    def undo_level_skillpoints(cls, char, level, points):
        char.lose_skill_points(points)

    @classmethod
    def respond_to_event(cls, event, responses):
        super(Class, cls).respond_to_event(event, responses)
        for lvl in tuple(l for l in cls.levels
                         if l.level <= event.obj.classes[cls]):
            for f in lvl.special:
                f.respond_to_event(event, responses)


class GainFeat(pathfinder.characters.StaticCharacterFeature):
    name = "Feat"
    description = "Gain a feat."
    feat_type = 'general'

    @classmethod
    @pathfinder.events.event_handler('feat slots')
    def feat_slot(cls, event, responses):
        event.slots[cls.feat_type] += 1


class BonusFeat(GainFeat):
    """
    Grants a bonus feat.
    """
    name = 'Bonus Feat'
    description = "Gain a bonus combat feat."
    feat_type = 'combat'


