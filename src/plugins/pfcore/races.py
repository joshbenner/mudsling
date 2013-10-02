from pathfinder.races import Race

import pathfinder.sizes
import pathfinder.modifiers


class Dwarf(Race):
    name = 'Dwarf'
    plural = 'Dwarves'
    size = pathfinder.sizes.size_categories['medium']
    ability_modifiers = {
        'Constitution': 2,
        'Wisdom': 2,
        'Charisma': -2,
    }
    modifiers = pathfinder.modifiers.modifiers(
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