from flufl.enum import Enum

import mudsling.utils.units as units

from dice import Roll

from pathfinder.objects import MultipartThing, Equipment
import pathfinder.data


def enhancement(name):
    """
    Convenience method to retrieve a weapon enhancement by name from the data
    registry.

    :param name: The name of the enhancement to retrieve.
    :type name: str

    :return: The enhancement class.
    :rtype: pathfinder.enhancements.WeaponEnhancement
    """
    return pathfinder.data.get('WeaponEnhancement', name)


class Size(Enum):
    Small = 1
    Medium = 2
    Large = 3


class Encumbrance(Enum):
    Light = 1
    OneHanded = 2
    TwoHanded = 3


class Weapon(MultipartThing, Equipment):
    """
    A pathfinder weapon.
    """
    proficiency = 'simple'  # Training required to use the weapon.

    category = ''  # Melee, Projectile, etc
    family = ''    # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''      # Shortsword, Light crossbow, Beretta 92FS, etc

    size = Size.Medium
    encumbrance = Encumbrance.Light

    damage_roll = Roll('1d2')
    damage_type = 'bludgeoning'
    nonlethal = False
    threat = 20
    critical = 2
    range_increment = None

    #: List of attacks this weapon is designed to work with (non-improvised).
    #: :type: list of str
    attacks = []

    stat_defaults = {
        'attack': Roll('0'),
    }

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat == 'damage':
            return self.damage_roll
        return super(Weapon, self).get_stat_base(stat, resolved=True)

    def improvised_damage(self, attack_type):
        """
        Calculate the weapon damage roll this weapon does when used in an
        improvised fashion (ie, throwing a melee weapon, or striking with a
        ranged weapon).

        :param attack_type: The type of attack to calculate.
        :type attack_type: str

        :return: The improvised damage roll.
        :rtype: dice.Roll
        """
        if self.weight <= (3 * units.lbs):
            roll = '1d4'
        elif self.weight <= (6 * units.lbs):
            roll = '1d6'
        else:
            roll = '1d8'
        return Roll(roll)


class MeleeWeapon(Weapon):
    category = 'Melee'
    attacks = ['strike']


class RangedWeapon(Weapon):
    category = 'Projectile'
    attacks = ['shoot']
    range_increment = 10 * units.feet
