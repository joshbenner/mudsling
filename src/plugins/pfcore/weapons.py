from mudsling.utils.measurements import Dimensions as Dim

from pathfinder.things import Part
from pathfinder.weapons import MeleeWeapon, RangedWeapon
from pathfinder.combat import WieldType
from pathfinder.damage import DamageRoll, Damage

import pathfinder.characters
import pathfinder.errors

import pfcore
import pfcore.equipment


class Shortsword(MeleeWeapon):
    group = 'martial'
    family = 'Sword'
    type = 'Shortsword'
    cost = 10 * pfcore.gp

    wield_type = WieldType.Light

    melee_damage = DamageRoll('1d6', 'piercing')
    critical_threat = 19

    dimensions = Dim(32, 3.5, 1.5, 'inches')
    parts = {
        'blade': Part('Blade', 'steel', Dim(24, 3.5, 0.1, 'inches')),
        'hilt': Part('Hilt', 'wood', Dim(8, 1.5, 1.5, 'inches'))
    }


class Bow(RangedWeapon):
    """
    A generic arrow-consuming bow.
    """
    family = 'Bow'

    def consume_ammo(self, amount=1):
        """
        Bows consume arrows from worn quivers. Find the first non-empty quiver
        and use an arrow from it.
        """
        #: :type: pathfinder.characters.Character
        wielder = self.location
        if not pathfinder.characters.is_pfchar(wielder):
            raise pathfinder.errors.InsufficientAmmo()
        for worn in wielder.wearing:
            if worn.isa(pfcore.equipment.Quiver):
                #: :type: pfcore.equipment.Quiver
                quiver = worn
                if amount <= quiver.num_arrows():
                    for atype, num in quiver.arrow_inventory.items():
                        if num >= amount:
                            return atype
        raise pathfinder.errors.InsufficientAmmo()


class CompositeBow(Bow):
    """
    Composite bows can add up to their strength rating of user's strength mod
    to the damage the weapon inflicts. However, if user str mod is below the
    rating, they have a -2 to hit.
    """
    strength_rating = 0

    @classmethod
    def default_name(cls):
        name = super(CompositeBow, cls).default_name()
        return 'Composite %s (STR %d)' % (name, cls.strength_rating)

    def wielder_gets_bonus(self):
        who = self.wielded_by()
        if who is not None:
            str_mod = who.get_stat('str mod')
            return str_mod >= self.strength_rating
        return False

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)
        if stat == 'attack modifier':
            return 0 if self.wielder_gets_bonus() else -2
        return super(CompositeBow, self).get_stat_base(stat, resolved=True)

    def roll_ranged_damage(self, char, nonlethal, desc=False):
        damages = super(CompositeBow, self).roll_ranged_damage(char,
                                                               nonlethal,
                                                               desc=desc)
        if self.wielder_gets_bonus():
            extra = min(self.strength_rating,
                        self.wielded_by().get_stat('str mod'))
            damages = list(damages)
            damages.append(Damage(extra, 'piercing', nonlethal=nonlethal,
                                  desc=desc))
            damages = tuple(damages)
        return damages


class Longbow(Bow):
    group = 'martial'
    type = 'Longbow'
    cost = 75 * pfcore.gp

    wield_type = WieldType.TwoHanded

    ranged_damage = DamageRoll('1d8', 'piercing')
    critical_multiplier = 3

    dimensions = Dim(5 * 12, 1.5, 1.5, 'inches')
    parts = {
        'stave': Part('Stave', 'wood', Dim(5 * 12, 1.5, 1.5, 'inches')),
        'string': Part('String', 'rope', Dim(5 * 12, 0.1, 0.1, 'inches'))
    }


class CompositeLongbow(Longbow, CompositeBow):
    cost = 100 * pfcore.gp


class CompositeLongbow1(CompositeLongbow):
    cost = 200 * pfcore.gp
    strength_rating = 1


class CompositeLongbow2(CompositeLongbow):
    cost = 300 * pfcore.gp
    strength_rating = 2


class CompositeLongbow3(CompositeLongbow):
    cost = 400 * pfcore.gp
    strength_rating = 3


class CompositeLongbow4(CompositeLongbow):
    cost = 500 * pfcore.gp
    strength_rating = 4


class CompositeLongbow5(CompositeLongbow):
    cost = 600 * pfcore.gp
    strength_rating = 5


class Shortbow(Bow):
    group = 'martial'
    type = 'Shortbow'
    cost = 30 * pfcore.gp

    wield_type = WieldType.TwoHanded

    ranged_damage = DamageRoll('1d6', 'piercing')
    critical_multiplier = 3

    dimensions = Dim(3 * 12, 1.5, 1.5, 'inches')
    parts = {
        'stave': Part('Stave', 'wood', Dim(3 * 12, 1.5, 1.5, 'inches')),
        'string': Part('String', 'rope', Dim(3 * 12, 0.1, 0.1, 'inches'))
    }


class CompositeShortbow(Shortbow, CompositeBow):
    cost = 75 * pfcore.gp