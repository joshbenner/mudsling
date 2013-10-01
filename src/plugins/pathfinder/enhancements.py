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

    @classmethod
    def respond_to_event(cls, event, responses):
        """
        Enhancement modifiers are static-only -- that is, there is no need to
        wrap its modifiers in effects, since we need no state. Therefore, when
        an enhancement handles and event, it delegates directly to its
        modifiers.
        """
        for mod in cls.modifiers:
            mod.respond_to_event(event, responses)


class WeaponEnhancement(Enhancement):
    feature_type = 'weapon enhancement'


class ArmorEnhancement(Enhancement):
    feature_type = 'armor enhancement'
