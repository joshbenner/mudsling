import inspect

import mudsling.messages

import pathfinder.features
import pathfinder.objects
import pathfinder.combat
import pathfinder.damage
from pathfinder.events import event_handler
from pathfinder.modifiers import modifiers as mods


class Condition(pathfinder.features.Feature):
    """A condition is a state which affects an object or character.

    Conditions are instantiated upon association with an object.
    """
    __slots__ = ('source',)
    feature_type = 'condition'

    messages = mudsling.messages.Messages({
        'apply': {
            'subject': '{yYou are {r$feature{y.',
            '*': '$subject is {r$feature{n.',
        },
        'remove': {
            'subject': '{yYou are no longer {r$feature{y.',
            '*': '$subject is no longer {r$feature{n.'
        }
    })

    def __init__(self, source=None):
        self.source = source

    def apply_to(self, obj):
        super(Condition, self).apply_to(obj)
        if pathfinder.objects.is_pfobj(obj):
            obj.trigger_event(pathfinder.objects.events.condition_applied,
                              condition=self)

    def remove_from(self, obj):
        super(Condition, self).remove_from(obj)
        if pathfinder.objects.is_pfobj(obj):
            obj.trigger_event(pathfinder.objects.events.condition_removed,
                              condition=self)

    def _show_msg(self, obj, msg):
        if (not isinstance(self.source, Condition)
                and not (inspect.isclass(self.source)
                         and issubclass(self.source, Condition))):
            super(Condition, self)._show_msg(obj, msg)


class FlatFooted(Condition):
    name = 'Flat-Footed'
    description = "The character is unable to react normally due to surprise"\
                  " or warming up to the required activity level, losing"\
                  " their DEX bonus to AC and CMD, and unable to make attacks"\
                  " of opportunity."

    @event_handler('allow defensive dex bonus')
    def deny_dex_bonus(self, event, responses):
        return False


class Immobilized(Condition):
    name = 'Immobilized'
    description = 'Unable to move.'


class Incapable(Condition):
    name = 'Incapable'
    description = 'Unable to attack or perform most actions other than move.'


class Helpless(Condition):
    name = 'Helpless'
    modifiers = mods(
        'Become Incapable',
        'Become Immobilized',
        'Become Flat-Footed',
        '-4 to armor class against melee attacks',
        '-10 to Dexterity'  # Compromise from rules.
    )


class Unconscious(Condition):
    name = 'Unconscious'
    modifiers = mods('Become Helpless')

    @event_handler('has sense')
    def no_see_or_hear(self, event, responses):
        if event.sense in ('hearing', 'vision'):
            return False


class Staggered(Condition):
    """
    Condition primarily achieved by taking nonlethal damage equal to current
    hit points.
    """
    name = 'Staggered'
    description = "Character can move or act, but not both, in a single turn."

    @event_handler('combat action spent')
    def event_combat_action_spent(self, event, responses):
        if event.action_type in ('move', 'standard'):
            char = event.obj
            for action_type in ('move', 'standard'):
                remaining = char.remaining_combat_actions(action_type)
                if remaining:  # Prevent infinite recursion.
                    char.deduct_action(action_type, amount=remaining)


class Disabled(Condition):
    name = 'Disabled'
    description = "Character takes damage from standard actions."
    modifiers = mods('Become Staggered')

    @event_handler('combat action spent')
    def event_combat_action_spent(self, event, responses):
        if event.action_type == 'standard':
            event.obj.take_damage(1)


class Stable(Condition):
    name = 'Stable'
    modifiers = mods('Become Unconscious')
    description = "In a deadly condition, but not losing hit points."


class Dying(Condition):
    name = 'Dying'
    description = "Lose 1 hit point every round until death or stabilizing."
    modifiers = mods('Become Unconscious')

    def die_a_little(self, char):
        char.tell('{yYou are {rDYING{y!')
        char.take_damage(1)

    def respond_to_event(self, event, responses):
        if event.type == pathfinder.combat.events.round_ended:
            self.die_a_little(event.obj)
        elif event.type == pathfinder.combat.events.turn_started:
            event.obj.attempt_to_stabilize()
        elif event.type == pathfinder.objects.events.effect_timer:
            if not event.obj.attempt_to_stabilize():
                self.die_a_little(event.obj)


class Dead(Condition):
    name = 'Dead'
    modifiers = mods('Become Helpless')

    @event_handler('has sense')
    def no_see_or_hear(self, event, responses):
        if event.sense in ('hearing', 'vision'):
            return False


class Broken(Condition):
    name = 'Broken'
