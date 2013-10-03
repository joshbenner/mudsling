import wearables

import pathfinder.objects


class Equipment(pathfinder.objects.Thing):
    """
    Equipment is any thing which has a purpose and was probably crafted. The
    major difference is that equipment can have enhancements, whereas normal
    Things cannot.
    """
    #: Enhancements are feature instances that modify the object in some way.
    #: They can respond to events, such as stat modification.
    enhancements = []

    @property
    def features(self):
        features = list(self.enhancements)
        features.extend(super(Equipment, self).features)
        return features


class WearableEquipment(wearables.Wearable, Equipment):
    """
    Equipment that can be worn, such as armor, clothing, etc.

    .. todo:: Pockets, equipment slots, etc.
    """

    #: The thickness of the layer.
    layer_value = 1

    #: How many layers fit under this item.
    max_sublayers = 1

    #: The equipment slots this item occupies.
    occupy_slots = ()

    def before_wear(self, wearer):
        """
        Check to make sure the wearer has the require slots and not too many
        layers.

        :param wearer: The character to wear the equipment.
        :type wearer: pathfinder.characters.Character
        """
        raise NotImplemented
