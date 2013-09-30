import mudsling.messages

import pathfinder.features
import pathfinder.objects


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
