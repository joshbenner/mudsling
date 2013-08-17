from mudsling.messages import Messages

from .features import Feature
from .modifiers import modifiers as mods


class Condition(Feature):
    """A condition is a state which affects an object or character.

    Conditions are instantiated upon association with an object.
    """
    __slots__ = ('source',)
    feature_type = 'condition'

    messages = Messages({
        'apply': {
            'subject': '{yYou are {m$feature{y.',
            '*': '$subject is {m$feature{n.',
        },
        'remove': {
            'subject': '{yYou are no longer $feature.',
            '*': '$subject is no longer $feature.'
        }
    })

    def __init__(self, source=None):
        self.source = source

    def apply_to(self, obj):
        from .objects import is_pfobj
        super(Condition, self).apply_to(obj)
        if is_pfobj(obj):
            obj._apply_condition(self)


class Bleeding(Condition):
    name = 'Bleeding'


class Blind(Condition):
    name = 'Blind'


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
        '-2 to melee attack',
        '-2 to ranged attack',
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


class FlatFooted(Condition):
    name = 'Flat-Footed'

    def respond_to_event(self, event, responses):
        if event.name == 'allow defensive dex bonus':
            return False


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
    modifiers = mods('Become Incapable', 'Become Immobilized')


class Immobilized(Condition):
    name = 'Immobilized'
    description = 'Unable to move.'


class Incapable(Condition):
    name = 'Incapable'
    description = 'Unable to attack or perform most actions other than move.'


class Nauseated(Condition):
    name = 'Nauseated'
    description = 'Severe stomach distress that makes most actions impossible.'
    modifiers = mods('Become Incapable')


class Paralyzed(Condition):
    name = 'Paralyzed'


class Pinned(Condition):
    name = 'Pinned'


class Prone(Condition):
    name = 'Prone'


class Shaken(Condition):
    name = 'Shaken'


class Sickened(Condition):
    name = 'Sickened'


class Stable(Condition):
    name = 'Stable'


class Staggered(Condition):
    name = 'Staggered'


class Stunned(Condition):
    name = 'Stunned'


class Unconscious(Condition):
    name = 'Unconscious'
    modifiers = mods('Become Helpless')
