import re
import os
import logging

import mudsling.errors

#: :type: logging.Logger
logger = logging.getLogger('pathfinder')

import mudsling.config

import mudslingcore.ui
ui = mudslingcore.ui.ClassicUI()

from dice import Roll

import icmoney

# Other modules depend on this import.
from pathfinder import data
from pathfinder import sizes

#: Indicates if all pathfinder-related data has been loaded. Once data loading
#: is complete, some pieces of code will begin to attempt to access data, such
#: as modifiers, which can be loaded before the data they depend on.
data_loaded = False

config = mudsling.config.Config()
config.read(os.path.join(os.path.dirname(__file__), 'defaults.cfg'))
#: @type: L{mudsling.config.ConfigSection}
config = config['pathfinder']

abilities = ['strength', 'dexterity', 'constitution', 'intelligence',
             'wisdom', 'charisma']
abil_short = ['str', 'dex', 'con', 'int', 'wis', 'cha']

feature_re = re.compile('^(?P<name>.*?)(?: +\((?P<subtype>.*)\))?$')

# Styles for use with ui.conditional_style.
bonus_style = (('<', 0, '{r'), ('>', 0, '{g'), ('=', 0, '{y'))

# Simple roll cache.
_rolls = {
    '1d20': Roll('1d20')
}


def roll(expr, desc=False):
    """
    Convenience die roller. Supports no variables -- only for straight dice.
    Will cache the roll objects to make subsequent rolls of same type more
    efficient.

    :param expr: The roll to cast.
    :type expr: str

    :return: Tuple containing the roll result and the optional description.
    :rtype: int or float or tuple
    """
    if expr not in _rolls:
        _rolls[expr] = Roll(expr)
    return _rolls[expr].eval(desc=desc)


def succeeds(natural, total, target_number, always_succeeds=20):
    """
    Convenience function to evaluate if a roll succeeded.
    """
    return ((always_succeeds and natural >= always_succeeds)
            or total >= target_number)


# By declaring currencies, they are automatically registered.
icmoney.Currency('pp', 'Platinum Piece', 10.0)
icmoney.Currency('gp', 'Gold Piece', 1.0)
icmoney.Currency('sp', 'Silver Piece', 0.1)
icmoney.Currency('cp', 'Copper Piece', .001)


# Default damage rolls for objects ob various sizes.
improvised_damage = {
    sizes.Fine: Roll('0'),
    sizes.Diminutive: Roll('1d1'),
    sizes.Tiny: Roll('1d2'),
    sizes.Small: Roll('1d4'),
    sizes.Medium: Roll('1d8'),
    sizes.Large: Roll('1d20'),
    sizes.Huge: Roll('2d20'),
    sizes.Gargantuan: Roll('4d20'),
    sizes.Colossal: Roll('6d20')
}


class Damage(object):
    """
    Represents the damage done in an instance of damage being done.

    Damage objects are short-lived only! Do not store damage objects.
    """
    __slots__ = ('types', 'points', 'nonlethal')

    def __init__(self, points, types, nonlethal=False):
        self.points = points
        if isinstance(types, (list, tuple, set)):
            self.types = tuple(types)
        self.types = (str(types),)
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


def parse_feat(name):
    m = feature_re.match(name)
    if not m:
        raise mudsling.errors.FailedMatch('No such feat: %s' % name)
    info = m.groupdict()
    try:
        feat = data.match(info['name'], types=('feat',))
    except mudsling.errors.FailedMatch:
        raise mudsling.errors.FailedMatch('No such feat: %s' % info['name'])
    return feat, info['subtype']
