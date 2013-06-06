from .features import Feature
from .data import loaded_data


class Skill(Feature):
    __metaclass__ = loaded_data
    __slots__ = ('id', 'name', 'description', 'ability', 'trained_only',
                 'ac_penalty')
