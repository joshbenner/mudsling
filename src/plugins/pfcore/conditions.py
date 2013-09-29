from pathfinder.conditions import Condition
from pathfinder.modifiers import modifiers as mods


class Bleeding(Condition):
    name = 'Bleeding'


class Blind(Condition):
    name = 'Blind'
    description = "Character cannot see, incurring penalties to AC and skill" \
                  " checks using STR or DEX, and loses their DEX bonus to AC."
    modifiers = mods(
        '-2 to armor class',
        '-4 to all strength-based skill checks',
        '-4 to all dexterity-based skill checks'
    )

    def respond_to_event(self, event, responses):
        if event.name == 'allow defensive dex bonus':
            return False


class Broken(Condition):
    name = 'Broken'


class Dazed(Condition):
    named = 'Dazed'
    modifiers = mods('Become Incapable')


class Dazzled(Condition):
    name = 'Dazzled'
    modifiers = mods(
        '-1 to melee attack',
        '-1 to ranged attack',
        '-1 to Perception checks'
    )


class Dead(Condition):
    name = 'Dead'
    modifiers = mods('Become Helpless')


class Deaf(Condition):
    name = 'Deaf'
    modifiers = mods(
        '-4 to initiative',
        '-4 to Perception checks'
    )


class Disabled(Condition):
    name = 'Disabled'
    description = "Character can move or act, but not both, in a single turn."


class Dying(Condition):
    name = 'Dying'
    modifiers = mods('Become Unconscious')


class Entangled(Condition):
    name = 'Entangled'
    modifiers = mods(
        '-2 to all attacks',
        '-4 to Dexterity'
    )


class Exhausted(Condition):
    name = 'Exhausted'
    modifiers = mods(
        '-6 to Strength',
        '-6 to Dexterity'
    )


class Fatigued(Condition):
    name = 'Fatigued'
    modifiers = mods(
        '-2 to Strength',
        '-2 to Dexterity'
    )


class Grappled(Condition):
    name = 'Grappled'
    modifiers = mods(
        'Become Immobilized',
        '-2 to all attacks',
        '-2 to all saves',
        '-2 to all skill checks',
        '-2 to all ability checks',
    )


class Helpless(Condition):
    name = 'Helpless'
    modifiers = mods(
        'Become Incapable',
        'Become Immobilized',
        'Become Flat-Footed',
        '-4 to armor class against melee attacks',
        '-10 to Dexterity'  # Compromise from rules.
    )


class Nauseated(Condition):
    name = 'Nauseated'
    description = 'Severe stomach distress that makes most actions impossible.'
    modifiers = mods('Become Incapable')


class Paralyzed(Condition):
    name = 'Paralyzed'
    modifiers = mods(
        'Become Helpless',
        '-10 to Srength'
    )


class Pinned(Condition):
    name = 'Pinned'
    modifiers = mods(
        'Become Immobilized',
        'Become Incapable',
        '-10 to Dexterity',
        '-4 to armor class'
    )


class Prone(Condition):
    name = 'Prone'
    modifiers = mods(
        '-4 to melee attack',
        '+4 to armor class against ranged attacks',
        '-4 to armor class against melee attacks'
    )


class Sickened(Condition):
    name = 'Sickened'
    modifiers = mods(
        '-2 to all attacks',
        '-2 to all damage rolls',
        '-2 to all saves',
        '-2 to all skill checks',
        '-2 to all ability checks'
    )


class Stable(Condition):
    name = 'Stable'
    modifiers = mods('Become Unconcious')


class Staggered(Condition):
    name = 'Staggered'
    description = "Character can move or act, but not both, in a single turn."
    # Condition primarily achieved by taking nonlethal damage equal to current
    # hit points.


class Stunned(Condition):
    name = 'Stunned'
    modifiers = mods(
        '-2 to armor class',
        '-4 to combat maneuver defense'
    )

    def respond_to_event(self, event, responses):
        if event.name == 'allow defensive dex bonus':
            return False


class Unconscious(Condition):
    name = 'Unconscious'
    modifiers = mods('Become Helpless')
