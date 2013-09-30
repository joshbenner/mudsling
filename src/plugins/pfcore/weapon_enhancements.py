from pathfinder.enhancements import WeaponEnhancement
from pathfinder.modifiers import modifiers as mods


class Masterwork(WeaponEnhancement):
    name = 'Masterwork'
    is_masterwork = True
    modifiers = mods(
        '+1 enhancement bonus to Attack'
    )


class Plus1(WeaponEnhancement):
    name = '+1'
    is_masterwork = True
    modifiers = mods(
        '+1 enhancement bonus to Attack',
        '+1 enhancement bonus to Damage'
    )


class Plus2(WeaponEnhancement):
    name = '+2'
    is_masterwork = True
    modifiers = mods(
        '+2 enhancement bonus to Attack',
        '+2 enhancement bonus to Damage'
    )


class Plus3(WeaponEnhancement):
    name = '+3'
    is_masterwork = True
    modifiers = mods(
        '+3 enhancement bonus to Attack',
        '+3 enhancement bonus to Damage'
    )


class Plus4(WeaponEnhancement):
    name = '+4'
    is_masterwork = True
    modifiers = mods(
        '+4 enhancement bonus to Attack',
        '+4 enhancement bonus to Damage'
    )


class Plus5(WeaponEnhancement):
    name = '+5'
    is_masterwork = True
    modifiers = mods(
        '+5 enhancement bonus to Attack',
        '+5 enhancement bonus to Damage'
    )
