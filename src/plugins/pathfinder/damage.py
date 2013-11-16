import inspect

import mudsling.storage
import mudsling.utils.object

from dice import Roll

import pathfinder.data


def damage_type(name):
    """
    Fetch a damage type from the registry.
    :param name: The name of the damage type to fetch.
    :return: The damage type class.
    :rtype: DamageType
    """
    if inspect.isclass(name) and issubclass(name, DamageType):
        return name
    return pathfinder.data.get(DamageType, name)


def match_type(name):
    if inspect.isclass(name) and issubclass(name, DamageType):
        return name
    return pathfinder.data.match(name, types=(DamageType,), exact=False)


def parse_damage_types(names):
    """
    Convert a string of damage types into a list of classes.
    :param names: String of damage type names.
    :return: Tuple of damage type classes.
    :rtype: tuple of DamageType
    """
    if isinstance(names, str):
        names = map(str.strip, names.split(','))
    if not isinstance(names, (tuple, list, set)):
        names = (names,)
    return map(match_type, names)


class DamageType(object):
    kind = 'physical'

    def __new__(cls, *a, **kw):
        """Do not allow instances of this static class."""
        return cls

    # noinspection PyNestedDecorators
    @mudsling.utils.object.ClassProperty
    @classmethod
    def name(cls):
        return cls.__name__


class DamageRoll(mudsling.storage.PersistentSlots):
    """
    A roll to calculate damage.
    """
    __slots__ = ('types', 'points_roll', 'nonlethal')

    def __init__(self, points_roll, types=()):
        if isinstance(points_roll, Roll):
            self.points_roll = points_roll
        else:
            self.points_roll = Roll(str(points_roll))
        self.types = parse_damage_types(types)

    def roll(self, pfobj, nonlethal=False, desc=False):
        """
        Roll the damage, as performed by a given PF object.

        :param pfobj: The object responsible for the damage. Usually the
            character involved.
        :param nonlethal: If the damage is non-lethal.
        :param desc: Whether or not to get a roll description.
        :rtype: Damage
        """
        rolldesc = None
        result = pfobj.roll(self.points_roll, desc=desc)
        if desc:
            result, rolldesc = result
        if result < 1:
            nonlethal = True
            result = 1
        return Damage(result, self.types, nonlethal, desc=rolldesc)


no_damage = DamageRoll(0)


class Damage(mudsling.storage.PersistentSlots):
    """
    A number of hit points of damage with one or more associated damage types.
    """
    __slots__ = ('points', 'types', 'nonlethal', 'desc')

    def __init__(self, points, types=(), nonlethal=False, desc=None):
        self.types = parse_damage_types(types)
        self.points = int(points)
        self.nonlethal = nonlethal
        self.desc = desc

    @property
    def full_desc(self):
        return "%s = %s" % (self.desc, self)

    def __str__(self):
        types = ', '.join([dt.name for dt in self.types])
        if self.nonlethal:
            types += ' (nonlethal)'
        return "%s %s" % (self.points, types)

    def __repr__(self):
        return 'Damage: %s' % self
