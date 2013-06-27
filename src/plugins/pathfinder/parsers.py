from mudsling.parsers import StaticParser, MatchDescendants
from mudsling import errors

import pathfinder
from pathfinder.characters import Character


class AbilityNameStaticParser(StaticParser):
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
        raise errors.ParseError("No ability matching '%s'." % input)

    @classmethod
    def unparse(cls, val, obj=None):
        return val


class StaticPFDataParser(StaticParser):
    data_types = None
    search_for = 'item'

    @classmethod
    def parse(cls, input):
        obj = pathfinder.data.match(input, types=cls.data_types)
        if obj is None:
            raise errors.ParseError("No %s '%s'." % (cls.search_for, input))
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


class MatchCharacter(MatchDescendants):
    def __init__(self, cls=Character, search_for='character', show=True):
        super(MatchCharacter, self).__init__(cls=cls,
                                             search_for=search_for,
                                             show=show)

    def _match(self, obj, input):
        if input == 'me' and obj.isa(self.objClass):
            return [obj]
        return super(MatchCharacter, self)._match(obj, input)
