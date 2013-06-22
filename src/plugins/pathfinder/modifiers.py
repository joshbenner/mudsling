"""
Modifiers are value-changers for stats, ability-grants, etc. Modifiers are put
to use as Effects, which are applied to PathfinderObjects.

BNF:
        name ::= <printables> (<printables> | " ")*
    rollexpr ::= <diceroll grammar>
      nature ::= "enhancement" | "racial" | "dodge"
        type ::= "bonus" | "penalty"
  damagetype ::= name
   damageval ::= <nums>+
    statname ::= name
      statvs ::= name
        stat ::= statname [("against" | "vs") statvs]
    timeunit ::= ("round" | "turn" | "second" | "minute" | "hour" | "day")["s"]
    duration ::= "for" rollexpr timeunit
       event ::= <printables>+
       until ::= "until" event
  expiration ::= duration | until
       bonus ::= rollexpr [nature] [type] ("to" | "on") stat
       grant ::= "grant"["s"] <alphanums>+ ["feat"]
       speak ::= ["can"] "speak"["s"] <alphanums>+
      resist ::= ["can" | "gain"["s"]] "resist"["s"] damagetype damageval
      reduct ::= ["gain"["s"]] "DR" damageval "/" (damagetype | "-")
    modifier ::= (bonus | resist | reduct | grant | speak) [expiration]

Examples:
* +2 to STR for 2 turns
* +1d4 + 1 enhancement bonus to Attack for 1 day
* +1d4 Damage
* Grants Darkvision
* Speak Common
* Resist fire 5

TODO:
"""
import logging

from pyparsing import ParseException
from flufl.enum import Enum

from mudsling.storage import PersistentSlots

import dice

logger = logging.getLogger('pathfinder')


class Types(Enum):
    bonus = 1
    damage_resistance = 2
    damage_reduction = 3
    grant = 4
    language = 5


def _grammar():
    from pyparsing import Optional, Suppress, StringEnd
    from pyparsing import SkipTo, WordStart, oneOf, Word, alphas, nums
    from pyparsing import Literal as L
    from pyparsing import CaselessLiteral as CL
    from pyparsing import CaselessKeyword as CK

    to = Suppress(CK("to") | CK("on"))

    type = (CK("bonus") | CK("penalty")).setResultsName("type")
    nature = (CK("enhancement") | CK("racial") | CK("dodge"))
    nature = nature.setResultsName("nature")
    modtype = Optional(nature, default='') + Optional(type, default='')

    timeunits = oneOf("round rounds turn turns second seconds minute minutes "
                      "hour hours day days", caseless=True)
    interval = dice.grammar + timeunits
    duration = (CK("for").suppress() + interval).setResultsName("duration")
    until = Suppress(CK("until")) + SkipTo(StringEnd()).setResultsName("until")
    expire = duration | until

    lastitem = SkipTo(expire | StringEnd())

    stat = WordStart() + lastitem.setResultsName("stat")
    val = SkipTo(modtype + to).setResultsName('mod_val')
    bonus = val + modtype + to + stat

    grant = Suppress(CK("grant") | CK("grants"))
    grant += WordStart() + lastitem.setResultsName("grant")

    lang = Suppress(CK("speak") | CK("speaks"))
    lang += WordStart() + lastitem.setResultsName("language")

    damagetype = Word(alphas, alphas + ' ')
    damageval = Word(nums)
    gain = CK("gain") | CK("gains")
    resist = Optional(CK("can") | gain)
    resist += (CK("resist") | CK("resists"))
    resist += damagetype.setResultsName("resist type")
    resist += damageval.setResultsName("resist value")

    reduct = gain + CL("DR")
    reduct += damageval.setResultsName("reduction value")
    reduct += L('/') + (damagetype | L('-')).setResultsName("reduction type")

    modifier = (bonus | resist | reduct | grant | lang) + Optional(expire)

    return modifier

grammar = _grammar()


class Modifier(PersistentSlots):
    """
    Represents a modifier that can be provided by equipment, conditions, class
    features, etc (just about anything).

    This class is a stored modifier, as opposed to an mod that is currently
    applied to an object/character.
    """
    __slots__ = ('original', 'type', 'payload', 'expiration')

    def __init__(self, mod_str, parser=None):
        self.original = mod_str
        parser = parser or grammar
        parsed = parser.parseString(mod_str, True)
        if 'grant' in parsed:
            self.type = Types.grant
            self.payload = parsed['grant'].strip().lower()
        elif 'language' in parsed:
            self.type = Types.language
            self.payload = parsed['language'].strip().lower()
        elif 'resist type' in parsed:
            self.type = Types.damage_resistance
            resist_type = parsed['resist type'].strip().lower()
            resist_value = int(parsed['resist value'].strip())
            self.payload = (resist_value, resist_type)
        elif 'reduction type' in parsed:
            self.type = Types.damage_reduction
            reduction_type = parsed['reduction type'].strip().lower()
            reduction_value = int(parsed['reduction value'].strip())
            self.payload = (reduction_value, reduction_type)
        else:
            self.type = Types.bonus
            roll = (dice.Roll(parsed['mod_val'][0]) if 'mod_val' in parsed
                    else None)
            nature = parsed.get('nature', '').strip().lower() or None
            type = parsed.get('type', '').strip().lower() or None
            stat = parsed.get('stat', '').strip().lower() or None
            self.payload = (roll, stat, type, nature)
        self.expiration = None
        if 'until' in parsed:
            self.expiration = parsed['until'].strip().lower()
        if 'duration' in parsed:
            val, unit = parsed['duration']
            duration_roll = dice.Roll(val)
            duration_unit = unit.rstrip('s')
            self.expiration = (duration_roll, duration_unit)

    def __str__(self):
        return self.original

    def __repr__(self):
        return 'Modifier: %s' % self.original


def modifiers(*a):
    mods = []
    for mod_str in a:
        try:
            e = Modifier(mod_str)
        except ParseException:
            logger.warning("Could not parse modifier: %s" % mod_str)
        else:
            mods.append(e)
    return mods
