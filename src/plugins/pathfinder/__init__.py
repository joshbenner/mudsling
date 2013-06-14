# from collections import namedtuple
# from collections import OrderedDict

# API-access imports: make important stuff easy to access.
from .objects import Character, Thing
from .sizes import size, size_categories
from pathfinder import data

abilities = ['Strength', 'Dexterity', 'Constitution', 'Intelligence',
             'Wisdom', 'Charisma']
abil_short = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']


class Damage(object):
    """
    Represents the damage done in an instance of damage being done.

    Damage objects are short-lived only! Do not store damage objects.
    """
    __slots__ = ('type', 'points', 'nonlethal')

    def __init__(self, points, type, nonlethal=False):
        self.points = points
        self.type = type
        self.nonlethal = nonlethal
