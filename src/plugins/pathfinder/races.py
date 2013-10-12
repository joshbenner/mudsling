import pathfinder.characters
import pathfinder.sizes
import pathfinder.modifiers
import pathfinder.data


class Race(pathfinder.characters.CharacterFeature):
    """
    A race.

    Races should not be instantiated.
    """
    name = ''
    plural = ''
    size = None
    ability_modifiers = {}
    modifiers = []
    genders = ('male', 'female')

    @classmethod
    def respond_to_event(cls, event, responses):
        return cls.class_respond_to_event(event, responses)

    @classmethod
    def apply_to(cls, char):
        from .characters import is_pfchar
        if not is_pfchar(char):
            return
        char.size_category = cls.size
        mods = []
        for abil, val in cls.ability_modifiers.iteritems():
            bonus = pathfinder.format_modifier(val)
            mods.append(pathfinder.modifiers.Modifier(
                bonus + ' to ' + abil.capitalize(),
                source=cls
            ))
        mods.extend(cls.modifiers)
        for mod in mods:
            char.apply_effect(mod)

    @classmethod
    def remove_from(cls, char):
        from .characters import is_pfchar
        if not is_pfchar(char):
            return
        char.remove_effects_by_source(cls)
