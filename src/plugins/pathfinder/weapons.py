from dice import Roll

from pathfinder.objects import MultipartThing, Equipment, attack
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


class Weapon(MultipartThing, Equipment):
    """
    A pathfinder weapon.
    """
    proficiency = 'simple'  # Training required to use the weapon.

    category = ''  # Melee, Projectile, etc
    family = ''    # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''      # Shortsword, Light crossbow, Beretta 92FS, etc

    melee_damage = Roll('0')
    ranged_damage = Roll('0')

    def get_stat_default(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)
        if stat == 'melee damage':
            return self.melee_damage
        elif stat == 'ranged damage':
            return self.ranged_damage
        return super(Weapon, self).get_stat_default(stat, True)


class MeleeWeapon(Weapon):
    category = 'Melee'

    @attack('strike', default=True)
    def melee_attack(self, actor, target):
        raise NotImplemented

    def improvised_melee_attack(self, actor, target):
        """Override without @attack to disable improvised attack from parent."""
        pass


class RangedWeapon(Weapon):
    category = 'Projectile'

    @attack('shoot', default=True)
    def ranged_attack(self, actor, target):
        raise NotImplemented
