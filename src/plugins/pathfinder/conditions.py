import inspect

import mudsling.messages

import pathfinder.features
import pathfinder.objects
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
            obj.trigger_event('condition applied', condition=self)

    def remove_from(self, obj):
        super(Condition, self).remove_from(obj)
        if pathfinder.objects.is_pfobj(obj):
            obj.trigger_event('condition removed', condition=self)

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

    def respond_to_event(self, event, responses):
        if event.name == 'allow defensive dex bonus':
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


class Staggered(Condition):
    name = 'Staggered'
    description = "Character can move or act, but not both, in a single turn."
    # todo: Implement action restriction.
    # Condition primarily achieved by taking nonlethal damage equal to current
    # hit points.


class Disabled(Condition):
    name = 'Disabled'
    description = "Character takes damage from standard actions."
    # Staggered is a related by distinct condition that is often added along
    # with disabled. However, you can recover and remove the disabled condition
    # while still being staggered.
    # todo: Implement additional impact, such as some actions causing damage.


class Stable(Condition):
    name = 'Stable'
    # Unconsciousness is not a direct result, but a related condition that is
    # likely to be added at the same time.
    # todo: Implement roll penalties equal to negative hit points.


class Dying(Condition):
    name = 'Dying'
    modifiers = mods('Become Unconscious')
    # todo: Implement HP loss.


class Dead(Condition):
    name = 'Dead'
    modifiers = mods(
        'Become Incapable',
        'Become Immobilized',
        'Become Deafened',
        'Become Blinded',
    )


class Broken(Condition):
    name = 'Broken'
