"""
Effects are modifiers that are applied to various stats on an object. Effects
can be provided by just about anything, and can apply to any Pathfinder object.

Effect syntax: <roll expr> [{bonus|penalty}] to <stat> [for <expr> round[s]]
* roll expr: The value of the effect.
* Bonus/penalty: no impact on value of effect, just flexiblity in effect text.
* stat: The stat of the subject impacted by the effect.

Examples:
* +2 to STR
* +1 bonus to Attack
* +1d4 Damage
"""
import re

from mudsling.storage import Persistent

import dice

effect_re = re.compile("^(.+?)(?: +bonus| +penalty)? +to +(.+?)"
                       "(?: +for +(.+) +(?:rounds?|turns?))?$", re.I)


class Effect(Persistent):
    def __init__(self, effectstr):
        rollstr, stat, rounds = effect_re.match(effectstr).groups()
        self.roll = dice.Roll(rollstr)
        self.stat = stat
        self.duration = rounds
