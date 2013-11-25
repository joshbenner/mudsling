from pathfinder.conditions import Condition
from pathfinder.modifiers import modifiers as mods
from pathfinder.events import event_handler


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

    @event_handler('allow defensive dex bonus')
    def deny_dex_bonus(self, event, responses):
        return False

    @event_handler('has sense')
    def cannot_see(self, event, responses):
        if event.sense == 'vision':
            return False


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


class Deaf(Condition):
    name = 'Deaf'
    modifiers = mods(
        '-4 to initiative',
        '-4 to Perception checks'
    )

    @event_handler('allow defensive dex bonus')
    def deny_dex_bonus(self, event, responses):
        return False

    @event_handler('has sense')
    def cannot_hear(self, event, responses):
        if event.sense == 'hearing':
            return False


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


class Stunned(Condition):
    name = 'Stunned'
    modifiers = mods(
        '-2 to armor class',
        '-4 to combat maneuver defense'
    )

    @event_handler('allow defensive dex bonus')
    def deny_dex_bonus(self, event, responses):
        return False
