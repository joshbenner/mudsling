import re
import os
import logging

import mudsling.errors

#: :type: logging.Logger
logger = logging.getLogger('pathfinder')

import mudsling.config

import mudslingcore.ui
ui = mudslingcore.ui.ClassicUI()

from pathfinder import data

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
