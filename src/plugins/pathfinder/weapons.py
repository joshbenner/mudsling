import mudsling.utils.units as units
from mudsling.utils.measurements import Dimensions as Dim

from dice import Roll

import pathfinder.objects
from pathfinder.objects import Part


class Weapon(pathfinder.objects.MultipartThing):
    """
    A pathfinder weapon.
    """
    category = ''  # Melee, Projectile, etc
    family = ''    # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''      # Shortsword, Light crossbow, Beretta 92FS, etc

    damage_roll = Roll('1d2')
    damage_type = 'bludgeoning'
    nonlethal = False
    threat = 20
    critical = 2
    range_increment = None

    #: List of attacks this weapon is designed to work with (non-improvised).
    #: :type: list of str
    attacks = []

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


class Shortsword(MeleeWeapon):
    family = 'Sword'
    type = 'Shortsword'
    damage_roll = Roll('1d6')
    damage_type = 'piercing'
    threat = 19
    dimensions = Dim(32, 3.5, 1, 'inches')
    parts = {
        'blade': Part('Blade', 'steel', Dim(24, 3.5, 0.1, 'inches')),
        'hilt': Part('Hilt', 'wood', Dim(8, 1, 1, 'inches'))
    }
