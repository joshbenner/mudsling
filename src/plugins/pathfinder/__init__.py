# from collections import namedtuple
# from collections import OrderedDict

import os
import inflect
inflection = inflect.engine()

import logging
logger = logging.getLogger('pathfinder')

from mudslingcore.ui import ClassicUI
ui = ClassicUI()
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

abilities = ['strength', 'dexterity', 'constitution', 'intelligence',
             'wisdom', 'charisma']
abil_short = ['str', 'dex', 'con', 'int', 'wis', 'cha']

# Styles for use with ui.conditional_style.
bonus_style = (('<', 0, '{r'), ('>', 0, '{g'))


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


def format_modifier(mod, color=False, style=bonus_style):
    s = ('+' if mod >= 0 else '') + str(mod)
    return (ui.conditional_style(mod, styles=style, alternate=s) if color
            else s)
format_mod = format_modifier  # Short-version (convenience).


def format_range(low, high, force_range=False, color=False, style=bonus_style):
    if low == high and not force_range:
        return ui.conditional_style(low, styles=style) if color else str(low)
    high_ = ('(%s)' % high) if high < 0 else str(high)
    if color:
        high_ = ui.conditional_style(high, styles=style, alternate=high_)
        low_ = ui.conditional_style(low, styles=style, suffix='{n')
    else:
        low_ = low
    return "%s-%s" % (low_, high_)
