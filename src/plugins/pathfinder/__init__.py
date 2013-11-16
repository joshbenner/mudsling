import re
import os
import logging

import mudsling.errors
import mudsling.storage

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


class RollResult(mudsling.storage.PersistentSlots):
    """
    A roll result from a base roll (whose result is the 'natural' result)
    modified by a series of modifiers.
    """
    __slots__ = ('roll', 'mods', 'state', 'desc', 'natural', 'total', 'vs',
                 'success')

    def __init__(self, base_roll, mods=None, state=None, vs=None,
                 always_succeeds=None, **vars):
        """
        :param base_roll: The base roll to perform. Usually only a diespec.
        :type base_roll: str

        :param mods: Any modifiers to the base roll.
        :type mods: None or dict

        :param state: The roll expression's initial state.
        :type state: None or dict

        :param vars: Any additional variables to use in the expression.
        :type vars: dict
        """
        state = state if state is not None else {}
        state['desc'] = True
        self.roll = base_roll
        self.mods = mods
        self.vs = vs
        self.state = state
        self.natural, desc = roll(base_roll, state=state, desc=True, **vars)
        total = self.natural
        if mods is not None:
            for mod_key, mod in mods.iteritems():
                if isinstance(mod, basestring):
                    mod = Roll(mod)
                if isinstance(mod, Roll):
                    mod_val, mod_desc = mod.eval(state=state, desc=True, **vars)
                else:
                    mod_val = mod
                    mod_desc = "%s(%s)" % (mod_key, mod_val)
                total += mod_val
                desc += ' + %s' % mod_desc
        self.total = total
        self.desc = desc
        if self.vs is not None:
            if always_succeeds is None:
                always_succeeds = _cached_roll(base_roll).max
            self.success = succeeds(self.natural, self.total, vs,
                                    always_succeeds=always_succeeds)
        else:
            self.success = None

    @property
    def full_desc(self):
        return '%s = %s' % (self.desc, self.total)

    def success_desc(self, win='SUCCESS', fail='FAIL', vs_name=''):
        if self.success is None:
            r = '?'
        else:
            r = win if self.success else fail
        vs = ('%s %s' % (vs_name, self.vs)).strip()
        return "%s vs %s: %s" % (self.full_desc, vs, r)


class D20Result(RollResult):
    """
    A convenience roll result implementing the core mechanic of D20.
    """

    def __init__(self, mods=None, state=None, **vars):
        super(D20Result, self).__init__('1d20', mods=mods, state=state, **vars)


# Simple roll cache.
_rolls = {
    '1d20': Roll('1d20')
}

def _cached_roll(expr):
    """
    Retrieved a cached roll object, creating it if necessary.
    """
    if expr not in _rolls:
        _rolls[expr] = Roll(expr)
    return _rolls[expr]


def roll(expr, state=None, desc=False, **vars):
    """
    Convenience die roller. Will cache the roll objects to make subsequent rolls
    of same type more efficient.

    :param expr: The roll to cast.
    :type expr: str

    :param state: The initial roll expression state.
    :type state: None or dict

    :param desc: Whether or not to get a roll description.
    :type desc: bool

    :param vars: Any additional variables to provide to the roll.
    :type vars: dict

    :return: Tuple containing the roll result and the optional description.
    :rtype: int or float or tuple
    """
    return _cached_roll(expr).eval(state=state, desc=desc, **vars)


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
