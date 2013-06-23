from mudsling.parsers import StaticParser
from mudsling import errors

import pathfinder


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
