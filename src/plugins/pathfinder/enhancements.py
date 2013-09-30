import pathfinder.features


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


class WeaponEnhancement(Enhancement):
    feature_type = 'weapon enhancement'


class ArmorEnhancement(Enhancement):
    feature_type = 'armor enhancement'
