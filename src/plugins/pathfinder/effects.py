"""
Effects are modifiers that are applied to various stats on an object. Effects
can be provided by just about anything, and can apply to any Pathfinder object.

Effect syntax: <roll expr> [{bonus|penalty}] to <stat> [<expiration>]
* roll expr: The value of the effect.
* Bonus/penalty: no impact on value of effect, just flexiblity in effect text.
* stat: The stat of the subject impacted by the effect.
    * <skill>|<ability> [mod[ifier]]|
* expiration: Turns, time, or event which expires the effect.
    * for <expr> {round|turn|second|minute|hour|day}[s]
    * until <event>

Examples:
* +2 to STR for 2 turns
* +1 bonus to Attack for 1 day
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
