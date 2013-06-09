# from collections import namedtuple
# from collections import OrderedDict

# API-access imports: make important stuff easy to access.
from .objects import Character, Thing
from .sizes import size, size_categories
from pathfinder import data


# class Ability(namedtuple("Ability", "name short")):
#     pass
#
# abilities = OrderedDict([(a.short.lower(), a) for a in [
#     Ability('Strength', 'STR'),
#     Ability('Dexterity', 'DEX'),
#     Ability('Constitution', 'CON'),
#     Ability('Intelligence', 'INT'),
#     Ability('Wisdom', 'WIS'),
#     Ability('Charisma', 'CHA'),
# ]])
#
#
# def ability(name):
#     n = name.lower()
#     if n in abilities:
#         return abilities[n]
#     for a in abilities.itervalues():
#         if a.name.lower() == n:
#             return a
#     raise KeyError("There is no '%s' ability" % name)
