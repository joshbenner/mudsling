"""
Modifiers are value-changers for stats, ability-grants, etc. Modifiers are put
to use as Effects, which are applied to PathfinderObjects.

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
    modifier ::= (bonus | grant | speak) [expiration]

Examples:
* +2 to STR for 2 turns
* +1d4 + 1 enhancement bonus to Attack for 1 day
* +1d4 Damage

TODO:
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
    modtype = Optional(nature, default=None) + Optional(type, default=None)

    timeunits = oneOf("round rounds turn turns second seconds minute minutes "
                      "hour hours day days", caseless=True)
    interval = dice.grammar + timeunits
    duration = (CK("for").suppress() + interval).setResultsName("duration")
    until = Suppress(CK("until")) + SkipTo(StringEnd()).setResultsName("until")
    expire = duration | until

    lastitem = SkipTo(expire | StringEnd())

    stat = WordStart() + lastitem.setResultsName("stat")
    val = dice.grammar.setResultsName("mod_val")
    bonus = val + Optional(modtype + to) + stat

    grant = Suppress(CK("grant") | CK("grants"))
    grant += WordStart() + lastitem.setResultsName("grant")

    lang = Suppress(CK("speak") | CK("speaks"))
    lang += WordStart() + lastitem.setResultsName("language")

    modifier = (bonus | grant | lang) + Optional(expire, default=None)

    return modifier

grammar = _grammar()


class Modifier(PersistentSlots):
    """
    Represents a modifier that can be provided by equipment, conditions, class
    features, etc (just about anything).

    This class is a stored modifier, as opposed to an mod that is currently
    applied to an object/character.
    """
    __slots__ = ('roll', 'nature', 'type', 'stat', 'expire_event',
                 'duration_roll', 'duration_unit', 'grant', 'lang')

    def __init__(self, mod_str, parser=None):
        parser = parser or grammar
        parsed = parser.parseString(mod_str, True)
        if 'grant' in parsed:
            self.grant = parsed['grant']
        elif 'language' in parsed:
            self.lang = parsed['language']
        else:
            self.roll = (dice.Roll(parsed['mod_val'])
                         if 'mod_val' in parsed
                         else None)
            if parsed.get('nature', None) is not None:
                self.nature = parsed['nature'].strip() or None
            else:
                self.nature = None
            if parsed.get('type', None) is not None:
                self.type = parsed['type'].strip() or None
            else:
                self.type = None
                # todo: Parse stat strings like "<skill> skill rolls" etc.
            self.stat = parsed['stat'].strip() if 'stat' in parsed else None
            if 'until' in parsed:
                self.expire_event = parsed['until']
            else:
                self.expire_event = None
            if 'duration' in parsed:
                val, unit = parsed['duration']
                self.duration_roll = dice.Roll(val)
                self.duration_unit = unit.rstrip('s')
            else:
                self.duration_roll = None
                self.duration_unit = None


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
