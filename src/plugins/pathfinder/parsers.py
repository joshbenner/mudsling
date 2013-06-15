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


class RaceStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        race = pathfinder.data.match(input, types=('race',))
        if race is None:
            raise errors.ParseError("No race '%s'." % input)
        return race

    @classmethod
    def unparse(cls, val, obj=None):
        return val.name
