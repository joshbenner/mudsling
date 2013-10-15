import pathfinder.equipment
import pathfinder.data
from pathfinder.combat import attack, DamageRoll
from pathfinder.things import MultipartThing


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


class Weapon(MultipartThing, pathfinder.equipment.Equipment):
    """
    A pathfinder weapon.
    """
    proficiency = 'simple'  # Training required to use the weapon.

    category = ''  # Melee, Projectile, etc
    family = ''    # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''      # Shortsword, Light crossbow, Beretta 92FS, etc


class MeleeWeapon(Weapon):
    category = 'Melee'
    melee_damage = DamageRoll(0)

    @attack('strike', default=True)
    def melee_attack(self, actor, target):
        raise NotImplemented

    def improvised_melee_attack(self, actor, target):
        """
        Override without @attack to disable improvised attack from parent.
        """
        pass

    def roll_melee_damage(self, char, desc=False):
        return self.melee_damage.roll(char, desc=desc)


class RangedWeapon(Weapon):
    category = 'Projectile'
    ranged_damage = DamageRoll(0)

    @attack('shoot', default=True)
    def ranged_attack(self, actor, target):
        raise NotImplemented

    def roll_ranged_damage(self, char, desc=False):
        return self.ranged_damage.roll(char, desc=desc)
