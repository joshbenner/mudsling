"""
Effects are modifiers that are applied to various stats on an object. Effects
can be provided by just about anything, and can apply to any Pathfinder object.

BNF:
        name ::= <printables> (<printables> | " ")*
    rollexpr ::= <diceroll grammar>
      nature ::= <alphanums> (<printables> | " ")*
        type ::= "bonus" | "penalty"
    statname ::= name
      statvs ::= name
        stat ::= statname [("against" | "vs") statvs]
    timeunit ::= ("round" | "turn" | "second" | "minute" | "hour" | "day")["s"]
    duration ::= "for" rollexpr timeunit
       event ::= <printables>+
       until ::= "until" event
  expiration ::= duration | until
       bonus ::= rollexpr [[nature] [type] ("to" | "on")] stat
       grant ::= "grant"["s"] <alphanums>+ ["feat"]
       speak ::= ["can"] "speak"["s"] <alphanums>+
      effect ::= (bonus | grant | speak) [expiration]

Examples:
* +2 to STR for 2 turns
* +1d4 + 1 enhancement bonus to Attack for 1 day
* +1d4 Damage

TODO:
* Implement vs checks (as separate class?)
* <expr> bonus to <stat> for <tags> (maybe same thing as vs/against?)
* Convert effects to slots.
* Implement overwriting effects, ie: CMB = BAB + max(STR, DEX) - Size Mod
"""
import re
from mudsling.storage import Persistent

import dice

_grant_re = re.compile("^Grants? +(.+?)(?: +feat)?$", re.I)
_speak_re = re.compile("^(?:Can +)Speaks? +(.+?)$", re.I)


def _grammar():
    from pyparsing import Optional, CaselessKeyword, Suppress, StringEnd
    from pyparsing import SkipTo, WordStart, oneOf

    CK = CaselessKeyword
    to = Suppress(CK("to") | CK("on"))

    type = (CK("bonus") | CK("penalty")).setResultsName("type")
    nature = WordStart() + SkipTo(type | to).setResultsName("nature")
    effecttype = Optional(nature, default=None) + Optional(type, default=None)

    timeunits = oneOf("round rounds turn turns second seconds minute minutes "
                      "hour hours day days", caseless=True)
    interval = dice.grammar + timeunits
    duration = (CK("for").suppress() + interval).setResultsName("duration")
    until = Suppress(CK("until")) + SkipTo(StringEnd()).setResultsName("until")
    expire = duration | until

    lastitem = SkipTo(expire | StringEnd())

    stat = WordStart() + lastitem.setResultsName("stat")
    val = dice.grammar.setResultsName("effect_val")
    bonus = val + Optional(effecttype + to) + stat

    grant = Suppress(CK("grant") | CK("grants"))
    grant += WordStart() + lastitem.setResultsName("grant")

    lang = Suppress(CK("speak") | CK("speaks"))
    lang += WordStart() + lastitem.setResultsName("language")

    effect = (bonus | grant | lang) + Optional(expire, default=None)

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
            self.nature = parsed['nature'].strip() or None
        if parsed['type'] is not None:
            self.type = parsed['type'].strip() or None
        # todo: Parse stat based on strings like "<skill> skill rolls" etc.
        self.stat = parsed['stat'].strip()
        if 'until' in parsed:
            self.expire_event = parsed['until']
        if 'duration' in parsed:
            val, unit = parsed['duration']
            self.duration_roll = dice.Roll(val)
            self.duration_unit = unit
