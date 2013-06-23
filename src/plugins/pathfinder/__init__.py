# from collections import namedtuple
# from collections import OrderedDict

import os
import inflect
inflection = inflect.engine()

import logging
logger = logging.getLogger('pathfinder')

from mudslingcore.ui import ClassicUI
import mudsling.config

# API-access imports: make important stuff easy to access.
from .objects import Thing
from .characters import Character
from .sizes import size, size_categories
from pathfinder import data

config = mudsling.config.Config()
config.read(os.path.join(os.path.dirname(__file__), 'defaults.cfg'))
#: @type: L{mudsling.config.ConfigSection}
config = config['pathfinder']

ui = ClassicUI()
abilities = ['strength', 'dexterity', 'constitution', 'intelligence',
             'wisdom', 'charisma']
abil_short = ['str', 'dex', 'con', 'int', 'wis', 'cha']


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


def format_modifier(mod):
    return ('+' if mod >= 0 else '') + str(mod)
