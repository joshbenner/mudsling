import pathfinder.features
import pathfinder.effects


class Enhancement(pathfinder.features.StaticFeature):
    """
    Enhancements are static classes which modify objects, especially weapons
    and armor.
    """
    feature_type = 'enhancement'

    #: Many different enhancements can cause an object to be considered a
    #: masterwork item.
    is_masterwork = False

    #: Enhancements carry a general value which is used to determine how much
    #: value and crafting difficulty the enhancement carries.
    value = 1

    _effect_cache = None

    @classmethod
    def respond_to_event(cls, event, responses):
        """
        Enhancements are unique in that they are not applied to their subjects
        via apply_to. Instead, they try to operate in a fully-static manner to
        avoid large memory consumption when there is a lot of equipment.

        So, when an event fires, enhancements will dynamically generate and
        cache the resulting effects, and use those to respond to the event
        directly, without delegating to the subject's .effects.
        """
        for effect in cls.effects():
            effect.respond_to_event(event, responses)

    @classmethod
    def effects(cls):
        """
        Convert the enhancement's modifiers into effect instances, which can
        respond to events. The result is cached so we only do this once per
        runtime per enhancement class.
        """
        if cls._effect_cache is None:
            cls._effect_cache = [pathfinder.effects.Effect(mod, source=cls)
                                 for mod in cls.modifiers]
        return cls._effect_cache


class WeaponEnhancement(Enhancement):
    feature_type = 'weapon enhancement'


class ArmorEnhancement(Enhancement):
    feature_type = 'armor enhancement'
