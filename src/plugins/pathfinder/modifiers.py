"""
Modifiers are value-changers for stats, ability-grants, etc.

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
      expire ::= duration | until
       bonus ::= rollexpr [nature] [type] ("to" | "on") stat
       grant ::= "grant"["s"] <alphanums>+ ["feat"]
      become ::= "become"["s"] <name>
       speak ::= ["can"] "speak"["s"] <alphanums>+
      resist ::= ["can" | "gain"["s"]] "resist"["s"] damagetype damageval
      reduct ::= ["gain"["s"]] "DR" damageval "/" (damagetype | "-")
    modifier ::= (bonus | resist | reduct | grant | cause | speak) [expire]

Examples:
* +2 to STR for 2 turns
* +1d4 + 1 enhancement bonus to Attack for 1 day
* +1d4 Damage
* Grants Darkvision
* Speak Common
* Resist fire 5
* Becomes Disabled

TODO:
"""
import logging

from pyparsing import ParseException
from flufl.enum import Enum

import mudsling.utils.object as obj_utils

import dice

import pathfinder
import pathfinder.errors
import pathfinder.events
import pathfinder.damage

logger = logging.getLogger('pathfinder')


class Types(Enum):
    bonus = 1
    damage_resistance = 2
    damage_reduction = 3
    grant = 4
    language = 5
    condition = 6


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

    become = Suppress(CK("become") | CK("becomes"))
    become += WordStart() + lastitem.setResultsName("condition")

    lang = Suppress(CK("speak") | CK("speaks"))
    lang += WordStart() + lastitem.setResultsName("language")

    damagetype = Word(alphas)
    damageval = Word(nums)
    gain = CK("gain") | CK("gains")
    resist = Optional(CK("can") | gain)
    resist += (CK("resist") | CK("resists"))
    resist += damagetype.setResultsName("resist type")
    resist += damageval.setResultsName("resist value")

    reduct = Optional(gain) + CL("DR")
    reduct += damageval.setResultsName("reduction value")
    reduct += L('/') + (damagetype | L('-')).setResultsName("reduction type")

    modifier = (bonus | resist | reduct | grant | become | lang)
    modifier += Optional(expire)

    return modifier

grammar = _grammar()


class Modifier(pathfinder.events.EventResponder):
    """
    Represents a modifier that can be provided by equipment, conditions, class
    features, etc (just about anything).

    Modifiers may be loaded/parsed before the data they reference is loaded.
    For instance, when a race is loaded, it may reference special abilities
    which have not yet been loaded. Therefore, we need to take a lazy approach
    to fully-parsing the modifier to its final data.

    Modifiers are intended to be static data, having only a single state which
    represents the modifier expression. So, while a modifier, for instance, has
    expiration data, that describes how long an effect applying the modifier
    would last instead of the modifier tracking expiration itself.
    """
    __slots__ = ('original', 'type', 'source', 'payload_desc', 'expiration')
    _transient_vars = ['payload_desc', 'expiration', 'type']

    def __init__(self, mod_str, parser=None, source=None):
        self.source = source
        self._parse_mod(mod_str, parser)

    @obj_utils.memoize_property
    def payload(self):
        """
        Try to resolve the payload to actual data. This may fail if all
        pathfinder data is not yet loaded.

        Some modifier instances will overwrite this property when the payload
        is not dependent on loaded data and is calculated at parse time.

        :raises: pathfinder.errors.DataNotReady
        :raises: pathfinder.errors.InvalidModifierType

        :rtype: any
        """
        if not pathfinder.data_loaded:
            raise pathfinder.errors.DataNotReady()
        if self.type == Types.grant:
            feat_class, subtype = pathfinder.parse_feat(self.payload_desc)
            return feat_class(subtype, source=self.source or self)
        elif self.type == Types.condition:
            condition_class = pathfinder.data.match(self.payload_desc,
                                                    types=('condition',))
            return condition_class(source=self.source or self)
        elif self.type == Types.language:
            return pathfinder.data.match(self.payload_desc,
                                         types=('language',))
        elif self.type in Types:  # Other types pass-thru the desc as value.
            return self.payload_desc
        else:
            raise pathfinder.errors.InvalidModifierType()

    def _parse_mod(self, mod_str, parser=None):
        self.original = mod_str
        parser = parser or grammar
        parsed = parser.parseString(mod_str, True)
        if 'grant' in parsed:
            self.type = Types.grant
            self.payload_desc = parsed['grant'].strip().lower()
        elif 'condition' in parsed:
            self.type = Types.condition
            self.payload_desc = parsed['condition'].strip().lower()
        elif 'language' in parsed:
            self.type = Types.language
            self.payload_desc = parsed['language'].strip().lower()
        elif 'resist type' in parsed:
            self.type = Types.damage_resistance
            resist_type = pathfinder.damage.match_type(
                parsed['resist type'].strip())
            resist_value = int(parsed['resist value'].strip())
            self.payload_desc = (resist_value, resist_type)
        elif 'reduction type' in parsed:
            self.type = Types.damage_reduction
            reduction_type = pathfinder.damage.match_type(
                parsed['reduction type'].strip())
            reduction_value = int(parsed['reduction value'].strip())
            self.payload_desc = (reduction_value, reduction_type)
        else:
            self.type = Types.bonus
            roll = (dice.Roll(parsed['mod_val'][0]) if 'mod_val' in parsed
                    else None)
            nature = parsed.get('nature', '').strip().lower() or None
            type = parsed.get('type', '').strip().lower() or None
            stat = parsed.get('stat', '').strip().lower() or None
            self.payload_desc = (roll, stat, type, nature)
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

    def __setstate__(self, state):
        super(Modifier, self).__setstate__(state)
        self._parse_mod(self.original)

    def event_stat_mods(self, event, responses):
        if self.type == Types.bonus:
            roll, stat, type, nature = self.payload
            stat_name, tags = event.obj.resolve_stat_name(stat)
            if event.stat == stat_name:
                if event.tags == () or event.tags == tags:
                    event.modifiers[self] = roll

    def event_feats(self, event, responses):
        if self.type == Types.grant:
            event.feats.append(self.payload)

    def event_conditions(self, event, responses):
        if self.type == Types.condition:
            event.conditions.append(self.payload)

    def event_spoken_languages(self, event, responses):
        if self.type == Types.language:
            event.languages.append(self.payload)

    def event_damage_reduction(self, event, responses):
        if self.type == Types.damage_reduction:
            value, vulnerable_to = self.payload
            if event.damage_type != vulnerable_to:
                responses[self] = value

    def event_damage_resistance(self, event, responses):
        if self.type == Types.damage_resistance:
            value, resist_type = self.payload
            if event.damage_type == resist_type:
                responses[self] = value

    event_callbacks = {
        'stat mods': 'event_stat_mods',
        'feats': 'event_feats',
        'conditions': 'event_conditions',
        'spoken languages': 'event_spoken_languages',
        'damage reduction': 'event_damage_reduction',
        'damage resistance': 'event_damage_resistance',
    }


def modifiers(*a, **kw):
    """
    Convenient way to define a list of modifiers.

    :param a: A list of modifier strings.
    :type a: list of str
    :param source: The source to pass to all modifiers. Must use keyword.
    :type source: any

    :return: A list of modifier instances.
    :rtype: list of Modifier
    """
    mods = []
    source = kw.get('source', None)
    for mod_str in a:
        try:
            e = Modifier(mod_str, source=source)
        except ParseException:
            logger.warning("Could not parse modifier: %s" % mod_str)
        else:
            mods.append(e)
    return mods
