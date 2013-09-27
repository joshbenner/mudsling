import dice

import pathfinder.objects


# class Attack(object):
#     __slots__ = ('damage_roll', 'dmg_type', 'nonlethal', 'threat', 'critical')
#
#     def __init__(self, damage_roll, dmg_type, nonlethal=False, threat=20,
#                  critical=2):
#         self.damage_roll = dice.Roll(damage_roll)
#         self.dmg_type = dmg_type
#         self.nonlethal = nonlethal
#         self.threat = threat
#         self.critical = critical


class Weapon(pathfinder.objects.Thing):
    """
    A pathfinder weapon.
    """
    category = ''  # Melee, Projectile, etc
    family = ''    # Sword, Knife, Bow, Handgun, Longarm, Shotgun, etc
    type = ''      # Shortsword, Light crossbow, Beretta 92FS, etc

    damage = ''
    damage_type = ''
    nonlethal = False
    threat = 20
    critical = 2

    #: Which of the weapon's attacks is its primary mode of attack.
    primary_attack = ''

    #: Dictionary of compatible attack types and their attack modifiers and
    #: damage rolls. Many weapons have only one attack.
    attacks = {}


class MeleeWeapon(Weapon):
    category = 'Melee'
    primary_attack = 'strike'


class RangedWeapon(Weapon):
    category = 'Projectile'
    primary_attack = 'shoot'


class Shortsword(MeleeWeapon):
    family = 'Sword'
    type = 'Shortsword'
    damage = '1d6'
    damage_type = 'piercing'
    threat = 19

    # attacks = {
    #     'strike': Attack('1d6', 'piercing', threat=19),
    # }
