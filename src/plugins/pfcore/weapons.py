from mudsling.utils.measurements import Dimensions as Dim

from dice import Roll

from pathfinder.objects import Part
from pathfinder.weapons import MeleeWeapon, Encumbrance


class Shortsword(MeleeWeapon):
    family = 'Sword'
    type = 'Shortsword'
    proficiency = 'martial'
    encumbrance = Encumbrance.Light

    damage_roll = Roll('1d6')
    damage_type = 'piercing'
    threat = 19

    dimensions = Dim(32, 3.5, 1, 'inches')
    parts = {
        'blade': Part('Blade', 'steel', Dim(24, 3.5, 0.1, 'inches')),
        'hilt': Part('Hilt', 'wood', Dim(8, 1, 1, 'inches'))
    }
