from .features import Feature
from .data import loaded_data
import pathfinder

from mudsling import parsers


class Skill(Feature):
    __metaclass__ = loaded_data
    __slots__ = ('id', 'name', 'ability', 'untrained', 'ac_penalty')

    def __init__(self, *a, **kw):  # Metaclass parses the keyword args.
        super(Skill, self).__init__(self.name)
        self.id = self.name
        self.ability = pathfinder.abilities[self.ability.lower()]
        self.untrained = parsers.BoolStaticParser.parse(self.untrained)
        self.ac_penalty = parsers.BoolStaticParser.parse(self.ac_penalty)
