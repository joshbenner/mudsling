import mudsling.objects
import mudsling.utils.string as string_utils
import mudsling.utils.units as units

import mudslingcore.objects
from pathfinder.things import Thing

import wearables

import pathfinder.objects
import pathfinder.characters
import pathfinder.errors


class Equipment(Thing, mudslingcore.objects.Container):
    """
    Equipment is any thing which has a purpose and was probably crafted. The
    major difference is that equipment can have enhancements, whereas normal
    Things cannot.
    """
    #: Enhancements are feature instances that modify the object in some way.
    #: They can respond to events, such as stat modification.
    enhancements = []

    #: The volume of carrying capacity in this piece of equipment.
    #: For convenience, see pathfinder.sizes.volume() for setting this value.
    #: :type: mudsling.utils.units._Quantity
    cargo_capacity = 0 * units.foot ** 3

    #: By default, equipment does not have a sealing mechanism.
    can_close = False

    def event_responders(self, event):
        responders = super(Equipment, self).event_responders(event)
        responders.extend(self.enhancements)
        return responders

    @classmethod  # Instances cannot override proficiencies.
    def valid_proficiencies(cls):
        """
        What proficiencies apply to this object?
        :rtype: set of any
        """
        #: :type: set of any
        return {cls}

    @property
    def used_cargo_capacity(self):
        """
        Return the cumulative volume occupied by the current contents of the
        equipment.
        :rtype: mudsling.utils.units._Quantity
        """
        volume = 0 * units.foot ** 3
        for o in self.contents:
            if pathfinder.objects.is_pfobj(o):
                # noinspection PyUnresolvedReferences
                volume += o.volume
        return volume

    @property
    def available_cargo_capacity(self):
        """
        How much volume is available for storage.
        :rtype: mudsling.utils.units._Quantity
        """
        return self.cargo_capacity - self.used_cargo_capacity

    def before_content_added(self, what, previous_location, by=None, via=None):
        """
        :type what: pathfinder.objects.PathfinderObject
        """
        super(Equipment, self).before_content_added(what, previous_location,
                                                    by, via)
        err = None
        msg = ''
        if not pathfinder.objects.is_pfobj(what):
            err = pathfinder.errors.InvalidContent
            if by.isa(mudsling.objects.Object):
                msg = "%s cannot be in %s" % (by.name_for(what),
                                              by.name_for(self))
            else:
                msg = "Incompatible object"
        if self.available_cargo_capacity < what.volume:
            err = pathfinder.errors.DoesNotFit
            if by.isa(mudsling.objects.Object):
                msg = "%s does not fit in %s" % (by.name_for(what),
                                                 by.name_for(self))
            else:
                msg = "Does not fit"
        if err is not None:
            raise err(what, previous_location, self.ref(), self.ref(), msg=msg)


class WearableEquipmentMetaClass(type):
    def __new__(mcs, name, parents, attr):
        """Make sure the body regions are lower case!"""
        regions = attr.get('body_regions', ())
        attr['body_regions'] = tuple(r.lower() for r in regions)
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
    body_regions = ()

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
        for region in self.body_regions:
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
