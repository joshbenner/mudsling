import mudsling.storage
import mudsling.utils.string as string_utils
import mudsling.utils.object as obj_utils

import pathfinder.equipment
import pathfinder.data
import pathfinder.errors
import pathfinder.modifiers
import pathfinder.objects
import pathfinder.characters
from pathfinder.combat import attack, simple_attack
from pathfinder.damage import DamageRoll
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
    group = 'simple'  # Proficiency required to use the weapon.
    category = ''     # Melee, Projectile, etc
    family = ''       # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''         # Shortsword, Light crossbow, Beretta 92FS, etc

    @classmethod
    def default_name(cls):
        return cls.type if cls.type else super(Weapon, cls).default_name()

    def wielded_by(self):
        #: :type: pathfinder.characters.Character
        who = self.location
        if (pathfinder.characters.is_pfchar(who)
                and self.ref() in who.wielded_weapons):
            return who
        return None

    @classmethod
    @obj_utils.memoize()
    def valid_proficiencies(cls):
        profs = super(Weapon, cls).valid_proficiencies()
        if cls.group:
            profs.add("%s weapons" % cls.group.lower())
        if cls.category:
            profs.add("%s weapons" % cls.category.lower())
        if cls.family:
            profs.add("%s weapons" % cls.family.lower())
            profs.add(string_utils.inflection.plural_noun(cls.family.lower()))
        if cls.type:
            profs.add(cls.type.lower())
            profs.add(string_utils.inflection.plural_noun(cls.type.lower()))
        return profs


class MeleeWeapon(Weapon):
    category = 'Melee'
    melee_damage = DamageRoll(0)

    melee_attack = simple_attack(group='strike', type='melee', mode='melee',
                                 default=True)

    improvised_melee_attack = None  # Hides attack-enabled ancestor.

    def roll_melee_damage(self, char, nonlethal, desc=False):
        return self.melee_damage.roll(char, nonlethal=nonlethal, desc=desc),


class RangedWeapon(Weapon):
    category = 'Projectile'
    ranged_damage = DamageRoll(0)

    def consume_ammo(self, amount=1):
        """
        Consumes the ammo used for a single shot.

        :param amount: How much ammo to consume.
        :type amount: int

        :raises: pathfinder.errors.InsufficientAmmo

        :returns: The ammo used.
        :rtype: Ammunition
        """
        raise pathfinder.errors.InsufficientAmmo()

    @attack('shoot', default=True, range=3)
    def ranged_attack(self, attacker, target, nonlethal=None, attack_mods=None,
                      improvised=False):
        ammo = self.consume_ammo()
        damage = self._standard_attack(attacker, target, 'ranged', 'ranged',
                                       nonlethal=nonlethal,
                                       attack_mods=attack_mods,
                                       improvised=improvised)
        if damage is not None:  # The shot hit, apply effects.
            extra_dmg = ammo.apply_effects(target)
            if extra_dmg:
                damage = list(damage)
                damage.extend(extra_dmg)
                damage = tuple(damage)
        return damage

    def roll_ranged_damage(self, char, nonlethal, desc=False):
        return self.ranged_damage.roll(char, nonlethal=nonlethal, desc=desc)


class Ammunition(mudsling.storage.PersistentSlots):
    """
    A type of ammunition.

    Ammunition will do the damage specified by the weapon firing it, but the
    ammunition can apply affects to the target that has been hit.
    """
    name = ''
    #: :type: list of (pathfinder.modifiers.Modifier, DamageRoll)
    effects = []

    @classmethod
    def apply_effects(cls, target):
        """
        Apply this ammunition's effects to a target.

        :param target: The target to which the effects will be applied.
        :type target: pathfinder.objects.PathfinderObject

        :returns: Any additional damage to do to target.
        :rtype: list of pathfinder.damage.Damage
        """
        damages = []
        if not pathfinder.objects.is_pfobj(target):
            return
        for effect in cls.effects:
            if isinstance(effect, pathfinder.modifiers.Modifier):
                target.apply_effect(effect, source=cls)
            elif isinstance(effect, DamageRoll):
                damages.append(effect.roll(target, desc=True))
        return damages
