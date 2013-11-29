import mudsling.commands
import mudsling.storage
import mudsling.utils.object as obj_utils
import mudsling.utils.units as units

from mudslingcore import objects as core_objects

import pathfinder
import pathfinder.combat
import pathfinder.commands.thing
import pathfinder.materials
import pathfinder.damage
from pathfinder.errors import PartNotFoundError
from pathfinder.objects import PathfinderObject


class Thing(core_objects.Thing, PathfinderObject, pathfinder.combat.Weapon):
    """
    Basic game world object that can interact with Pathfinder features. Things
    may be used as improvised weapons.
    """
    public_commands = mudsling.commands.all_commands(pathfinder.commands.thing)

    #: The object is designed to be used by creatures of this size.
    user_size = pathfinder.sizes.Medium

    improvised_melee_attack = pathfinder.combat.simple_attack(
        group='strike', type='melee', mode='melee', improvised=True,
        default=True)

    def roll_melee_damage(self, char, nonlethal, desc=False):
        roll = pathfinder.improvised_damage[self.size_category]
        dmg = pathfinder.damage.DamageRoll(roll, 'bludgeoning')
        return dmg.roll(char, nonlethal=nonlethal, desc=desc)

    @pathfinder.combat.attack('throw', improvised=True)
    def improvised_ranged_attack(self, actor, target):
        raise NotImplemented

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat in ('improvised melee damage', 'improvised ranged damage'):
            # Improvised damage is based on the size category of the object.
            return pathfinder.improvised_damage[self.size_category]
        return super(Thing, self).get_stat_base(stat, resolved=True)


class MaterialThing(Thing):
    """
    A Thing that is composed of materials, which determine its hitpoints and
    hardness.
    """
    #: The composition of the object. Keys are materials, values are the
    #: thickness in inches.
    materials = {}

    @property
    def permanent_hit_points(self):
        return int(max(1, sum(round(m.hp_per_inch * t, 0)
                              for m, t in self.materials.iteritems())))

    @property
    def hardness(self):
        return max(m.hardness for m, t in self.materials.iteritems() if t > 0)


class MultipartThing(Thing):
    """
    A Thing which has several parts, each with its own composition.
    """
    #: Keys are part names, values are dicts of material and thickness.
    parts = {}
    _part_damage = {}

    def on_object_created(self):
        super(MultipartThing, self).on_object_created()
        self._part_damage = {}

    @obj_utils.memoize_property
    def permanent_hit_points(self):
        """
        Dynamically calculate the permanent hit points of a multipart thing
        based on the hit points of its parts.
        :rtype: int
        """
        total_area = self.dimensions.surface_area
        hp = sum(float(p.max_hp * p.dimensions.surface_area / total_area)
                 for p in self.parts.itervalues())
        return max(1, int(round(hp, 0)))

    @property
    def hardness(self):
        """
        The object has the hardness of its hardest part.
        :rtype: int
        """
        return max(p.hardness for p in self.parts.itervalues())

    @obj_utils.memoize_property
    def weight(self):
        """
        Dynamically calculate the weight of the multipart thing based on the
        cumulative weight of all its parts.
        :rtype: mudsling.utils.units._Quantity
        """
        weight = 0 * units.lb
        # pint Quantities don't seem to like sum().
        for part in self.parts.itervalues():
            weight += part.weight
        return weight

    def get_part(self, id):
        """
        Returns a part object based on its ID.

        :param id: The identifying key used for the part in this object's list
            of parts.

        :return: The part.
        :rtype: Part

        :raises: PartNotFoundError
        """
        if id in self.parts:
            return self.parts[id]
        raise PartNotFoundError("No such part: %s" % id)

    def part_max_hp(self, id):
        """
        Obtain the maximum hit points of a part based on its ID.

        :param id: The ID of the part on this object.

        :return: The maximum possible HP of the part.
        :rtype: int
        """
        return self.get_part(id).max_hp

    def part_damage(self, id):
        """
        Obtain the amount of damage the identified part has suffered.

        :param id: The ID of the part on this object.

        :return: The points of damage suffered.
        :rtype: int
        """
        damage = self._part_damage.get(id, 0)
        return max(self.part_max_hp(id), damage)

    def part_remaining_hp(self, id):
        """
        Obtain the hit points remaining on the part.

        :param id: The ID of the part on this object.

        :return: The number of hit points remaining.
        :rtype: int
        """
        return self.part_max_hp(id) - self.part_damage(id)

    def part_area_ratios(self):
        """
        Return how much of the object each part comprises, based on surface
        area.

        :return: A dict of part ratios.
        :rtype: dict
        """
        areas = dict((name, part.dimensions.surface_area)
                     for name, part in self.parts.iteritems())
        total = sum(areas.itervalues())
        return dict((name, area / total) for name, area in areas)


class Part(mudsling.storage.PersistentSlots):
    __slots__ = ('name', 'material', 'dimensions')

    def __init__(self, name, material, dimensions):
        """
        :type name: str
        :type material: pathfinder.materials.Material or str
        :type dimensions: mudsling.utils.measurements.Dimensions
        """
        self.name = name
        if isinstance(material, pathfinder.materials.Material):
            self.material = material
        else:
            self.material = pathfinder.materials.Material(str(material))
        self.dimensions = dimensions

    @obj_utils.memoize_property
    def max_hp(self):
        """
        A part's maximum hit points are based on the material from which it is
        primarily made and its thickness, which is defined as the smallest
        dimension.

        :return: The maximum hit points this part may have.
        :rtype: int or float
        """
        _, thickness = self.dimensions.smallest_dimension()
        return self.material.hitpoints(thickness)

    @obj_utils.memoize_property
    def weight(self):
        """
        A part's weight is based on the density of the material from which it
        is primarily made.

        :return: The part's weight.
        :rtype: mudsling.utils.units._Quantity
        """
        return self.material.weight(self.dimensions)

    @property
    def hardness(self):
        return self.material.hardness
