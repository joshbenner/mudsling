import pathfinder
from .features import CharacterFeature
from .sizes import size_categories
from .modifiers import modifiers, Modifier
from .data import ForceSlotsMetaclass


class Race(CharacterFeature):
    """
    A race.

    Races should not be instantiated.
    """
    __metaclass__ = ForceSlotsMetaclass
    name = ''
    plural = ''
    size = None
    ability_modifiers = {}
    modifiers = []

    @classmethod
    def apply_to(cls, char):
        from .characters import is_pfchar
        if not is_pfchar(char):
            return
        char.size_category = cls.size
        mods = []
        for abil, val in cls.ability_modifiers.iteritems():
            bonus = pathfinder.format_modifier(val)
            mods.append(Modifier(bonus + ' to ' + abil.capitalize()))
        mods.extend(cls.modifiers)
        for mod in mods:
            char.apply_effect(mod, source=cls)

    @classmethod
    def remove_from(cls, char):
        from .characters import is_pfchar
        if not is_pfchar(char):
            return
        char.remove_effects_by_source(cls)


class Dwarf(Race):
    name = 'Dwarf'
    plural = 'Dwarves'
    size = size_categories['medium']
    ability_modifiers = {
        'Constitution': 2,
        'Wisdom': 2,
        'Charisma': -2,
    }
    modifiers = modifiers(
        'Grants Darkvision',
        '+4 dodge bonus to AC against giant subtype',
        '+2 racial bonus on Appraise skill checks',
        '+1 bonus to Attack against orc subtype',
        '+1 bonus to Attack against goblinoid subtype',
        '+2 racial bonus to saving throws against poison',
        '+2 racial bonus to saving throws against spells',
        '+2 racial bonus to saving throws against spell-like abilities',
        '+4 racial bonus to CMD against bull rush',
        '+4 racial bonus to CMD against trip',
        'Speak Common',
        'Speak Dwarven'
    )
