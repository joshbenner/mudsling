from mudsling.utils.measurements import Dimensions as Dim

from dice import Roll

from pathfinder.objects import Part, WieldType
from pathfinder.weapons import MeleeWeapon


class Shortsword(MeleeWeapon):
    family = 'Sword'
    type = 'Shortsword'
    proficiency = 'martial'

    wield_type = WieldType.Light

    melee_damage = Roll('1d6')
    damage_type = 'piercing'
    critical_threat = 19

    dimensions = Dim(32, 3.5, 1.5, 'inches')
    parts = {
        'blade': Part('Blade', 'steel', Dim(24, 3.5, 0.1, 'inches')),
        'hilt': Part('Hilt', 'wood', Dim(8, 1.5, 1.5, 'inches'))
    }
