import mudsling.parsers
import mudsling.errors
import mudsling.match

from mudsling import utils
import mudsling.utils.string

import mudslingcore.topography

import pathfinder
from .characters import Character


match_combatant = mudsling.parsers.MatchObject(cls=Character,
                                               search_for='combatant')


class AbilityNameStaticParser(mudsling.parsers.StaticParser):
    """
    Parse full ability name or abbreviation into the full name.
    """
    @classmethod
    def parse(cls, input):
        abil = input.lower().strip()
        if abil in pathfinder.abilities:
            return abil
        elif abil in pathfinder.abil_short:
            return pathfinder.abilities[pathfinder.abil_short.index(abil)]
        raise mudsling.errors.ParseError("No ability matching '%s'." % input)

    @classmethod
    def unparse(cls, val, obj=None):
        return val


class StaticPFDataParser(mudsling.parsers.StaticParser):
    data_types = None
    search_for = 'item'
    exact = True
    show_multiple = True

    @classmethod
    def plural(cls):
        return utils.string.inflection.plural(cls.search_for)

    @classmethod
    def parse(cls, input):
        try:
            obj = pathfinder.data.match(input, types=cls.data_types,
                                        exact=cls.exact,
                                        multiple=cls.show_multiple)
        except mudsling.errors.AmbiguousMatch as e:
            e.message = "Multiple %s match '%s'." % (cls.plural(), input)
            raise e
        except mudsling.errors.FailedMatch as e:
            e.message = "No %s match '%s'." % (cls.plural(), input)
            raise e

        if cls.show_multiple:
            if len(obj) > 1:
                msg = "Multiple %s match '%s': %s"
                msg = msg % (cls.plural(), input,
                             utils.string.english_list(obj))
                raise mudsling.errors.AmbiguousMatch(msg=msg)
            elif len(obj):
                obj = obj[0]
            else:
                obj = None

        if obj is None:
            raise mudsling.errors.ParseError("No %s '%s'."
                                             % (cls.search_for, input))
        return obj

    @classmethod
    def unparse(cls, val, obj=None):
        return val.name


class RaceStaticParser(StaticPFDataParser):
    data_types = ('race',)
    search_for = 'race'


class ClassStaticParser(StaticPFDataParser):
    data_types = ('class',)
    search_for = 'class'


class SkillStaticParser(StaticPFDataParser):
    data_types = ('skill',)
    search_for = 'skill'
    exact = False


class FeatStaticParser(mudsling.parsers.StaticParser):
    @classmethod
    def parse(cls, input):
        return pathfinder.parse_feat(input)

    @classmethod
    def unparse(cls, val, obj=None):
        if isinstance(val, tuple):
            feat, subtype = val
        else:
            feat = val
        return feat.name


class MatchCharacter(mudsling.parsers.MatchDescendants):
    def __init__(self, cls=Character, search_for='character', show=True):
        super(MatchCharacter, self).__init__(cls=cls,
                                             search_for=search_for,
                                             show=show)

    def _match(self, obj, input):
        if input == 'me' and obj.isa(self.objClass):
            return [obj]
        return super(MatchCharacter, self)._match(obj, input)


class MatchCombatArea(mudsling.parsers.Parser):
    """
    Parser to match a valid combat area in the combatant's location.
    """
    def parse(self, input, actor=None):
        """
        :param input: The input to parse.
        :type input: str
        :param actor: The actor performing the match.
        :type actor: pathfinder.characters.Character

        :return: The matched area or False.
        """
        if actor is None or not actor.has_location:
            return False
        #: :type: mudslingcore.topography.Room
        room = actor.location
        if not room.isa(mudslingcore.topography.Room):
            return False
        return room.match_combat_area(input)
