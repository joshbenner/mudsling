import mudsling.utils.string as string_utils

import wearables

import pathfinder.objects
import pathfinder.characters


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


class WearableEquipmentMetaClass(type):
    def __new__(mcs, name, parents, attr):
        """Make sure the body regions are lower case!"""
        regions = attr.get('occupy_body_regions', ())
        attr['occupy_body_regions'] = tuple(r.lower() for r in regions)
        return super(WearableEquipmentMetaClass, mcs).__new__(mcs, name,
                                                              parents, attr)


class WearableEquipment(Equipment, wearables.Wearable):
    """
    Equipment that can be worn, such as armor, clothing, etc.

    .. todo:: Pockets, equipment slots, etc.
    """
    __metaclass__ = WearableEquipmentMetaClass

    #: The thickness of the layer.
    layer_value = 1

    #: How many layers fit under this item.
    max_sublayers = 1

    #: The body regions this item occupies.
    occupy_body_regions = ()

    def before_wear(self, wearer):
        """
        Check to make sure the wearer has the required slots and not too many
        layers.

        :param wearer: The character to wear the equipment.
        :type wearer: pathfinder.characters.Character

        :raises: wearables.CannotWearError
        """
        super(WearableEquipment, self).before_wear(wearer)
        if not wearer.isa(pathfinder.characters.Character):
            return
        problems = []
        layers = wearer.body_region_layers()
        for region in self.occupy_body_regions:
            if region not in wearer.body_regions:
                problems.append('no %s' % region)
            elif layers[region] > self.max_sublayers:
                problems.append('too many layers on %s' % region)
        if len(problems):
            reasons = string_utils.english_list(problems)
            msg = 'You cannot wear %s: %s' % (wearer.name_for(self), reasons)
            raise wearables.CannotWearError(msg)

    def before_unwear(self, wearer):
        """
        Check to make sure the wearable is not covered by another article of
        clothing.

        :param wearer: The character wearing this equipment.
        :type wearer: pathfinder.characters.Character

        :raises: wearables.WearablesError
        """
        super(WearableEquipment, self).before_unwear(wearer)
        if not wearer.isa(pathfinder.characters.Character):
            return
        covering = wearer.covering_wearable(self)
        if len(covering):
            names = [wearer.name_for(w) for w in covering]
            msg = "Cannot unwear %s because it is covered by: %s"
            msg %= (wearer.name_for(self), string_utils.english_list(names))
            raise wearables.WearablesError(msg)
