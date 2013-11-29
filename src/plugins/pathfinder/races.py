import pathfinder.characters
import pathfinder.sizes
import pathfinder.modifiers
import pathfinder.data


class Race(pathfinder.characters.StaticCharacterFeature):
    """
    A race.

    Races should not be instantiated.
    """
    name = ''
    plural = ''
    size = None
    modifiers = []
    genders = ('male', 'female')

    @classmethod
    def apply_to(cls, char):
        from .characters import is_pfchar
        if not is_pfchar(char):
            return
        char.size_category = cls.size
