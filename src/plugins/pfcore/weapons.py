from mudsling.utils.measurements import Dimensions as Dim

from pathfinder.things import Part
from pathfinder.weapons import MeleeWeapon
from pathfinder.combat import WieldType
from pathfinder.damage import DamageRoll


class Shortsword(MeleeWeapon):
    group = 'martial'
    family = 'Sword'
    type = 'Shortsword'

    wield_type = WieldType.Light

    melee_damage = DamageRoll('1d6', 'piercing')
    critical_threat = 19

    dimensions = Dim(32, 3.5, 1.5, 'inches')
    parts = {
        'blade': Part('Blade', 'steel', Dim(24, 3.5, 0.1, 'inches')),
        'hilt': Part('Hilt', 'wood', Dim(8, 1.5, 1.5, 'inches'))
    }
