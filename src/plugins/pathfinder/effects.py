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
* <expr> bonus to <stat> for <tags> (maybe same thing as vs/against?)
* Convert effects to slots.
* Implement overwriting effects, ie: CMB = BAB + max(STR, DEX) - Size Mod
"""
import logging
from pyparsing import ParseException

from mudsling.storage import PersistentSlots

import dice

logger = logging.getLogger('pathfinder')


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


class Effect(PersistentSlots):
    """
    Represents an effect that can be provided by equipment, conditions, class
    features, etc (just about anything).

    This class is a *stored* effect, as opposed to an effect that is currently
    applied to an object/character.
    """
    __slots__ = ('roll', 'nature', 'type', 'stat', 'expire_event',
                 'duration_roll', 'duration_unit')

    def __init__(self, effect, parser=None):
        parser = parser or grammar
        parsed = parser.parseString(effect, True)
        self.roll = (dice.Roll(parsed['effect_val'])
                     if 'effect_val' in parsed
                     else None)
        if parsed.get('nature', None) is not None:
            self.nature = parsed['nature'].strip() or None
        else:
            self.nature = None
        if parsed.get('type', None) is not None:
            self.type = parsed['type'].strip() or None
        else:
            self.type = None
        # todo: Parse stat based on strings like "<skill> skill rolls" etc.
        self.stat = parsed['stat'].strip() if 'stat' in parsed else None
        if 'until' in parsed:
            self.expire_event = parsed['until']
        else:
            self.expire_event = None
        if 'duration' in parsed:
            val, unit = parsed['duration']
            self.duration_roll = dice.Roll(val)
            self.duration_unit = unit
        else:
            self.duration_roll = None
            self.duration_unit = None


def effects(*a):
    effects = []
    for effect_str in a:
        try:
            e = Effect(effect_str)
        except ParseException:
            logger.warning("Could not parse effect: %s" % effect_str)
        else:
            effects.append(e)
    return effects
