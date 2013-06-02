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

BNF:
  rollexpr ::= <diceroll grammar>
    nature ::= <alphanums> (<printables> | " ")*
      type :: = "bonus" | "penalty"
      stat ::= <printables>+
  timeunit ::= ("round" | "turn" | "second" | "minute" | "hour" | "day") ["s"]
  duration ::= "for" rollexpr timeunit
     event ::= <printables>+
     until ::= "until" event
expiration ::= duration | until
    effect ::= rollexpr [nature] [type] "to" stat [expiration]

Examples:
* +2 to STR for 2 turns
* +1d4 + 1 enhancement bonus to Attack for 1 day
* +1d4 Damage
"""
from mudsling.storage import Persistent

import dice


def _grammar():
    from pyparsing import Optional, CaselessKeyword, Suppress, StringEnd
    from pyparsing import SkipTo, WordStart, oneOf

    CK = CaselessKeyword

    to = CK("to").suppress()
    type = (CK("bonus") | CK("penalty")).setResultsName("type")
    nature = WordStart() + SkipTo(type | to).setResultsName("nature")
    effecttype = Optional(nature, default=None) + Optional(type, default=None)
    timeunits = oneOf("round rounds turn turns second seconds minute minutes "
                      "hour hours day days", caseless=True)
    interval = dice.grammar + timeunits
    duration = (CK("for").suppress() + interval).setResultsName("duration")
    until = Suppress(CK("until")) + SkipTo(StringEnd()).setResultsName("until")
    expire = duration | until
    stat = WordStart() + SkipTo(expire | StringEnd()).setResultsName("stat")
    val = dice.grammar.setResultsName("effect_val")
    effect = val + effecttype + to + stat + Optional(expire, default=None)

    return effect

grammar = _grammar()


class Effect(Persistent):
    """
    Represents an effect that can be provided by equipment, conditions, class
    features, etc (just about anything).

    This class is a *stored* effect, as opposed to an effect that is currently
    applied to an object/character.
    """
    roll = None
    nature = None
    type = None
    stat = ''
    expire_event = None
    duration_roll = None
    duration_unit = None

    def __init__(self, effect, parser=None):
        parser = parser or grammar
        parsed = parser.parseString(effect, True)
        self.roll = dice.Roll(parsed['effect_val'])
        if parsed['nature'] is not None:
            self.nature = parsed['nature'].strip()
        if parsed['type'] is not None:
            self.type = parsed['type'].strip()
        self.stat = parsed['stat'].strip()
        if 'until' in parsed:
            self.expire_event = parsed['until']
        if 'duration' in parsed:
            val, unit = parsed['duration']
            self.duration_roll = dice.Roll(val)
            self.duration_unit = unit
