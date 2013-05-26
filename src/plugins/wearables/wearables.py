"""
Wearables plugin.
"""

from mudsling.extensibility import GamePlugin
from mudsling.composition import hook, Feature, Featurized
from mudsling.commands import Command
from mudsling.messages import Messages
from mudsling.objects import Object
from mudsling import errors

from mudsling import utils
import mudsling.utils.string

from mudslingcore.objects import Thing, Character


def can_wear_wearables(who):
    return who.isa(Featurized) and WearingFeature in who.features


class WearablesPlugin(GamePlugin):
    def server_startup(self):
        Character.add_class_feature(WearingFeature)

    def object_classes(self):
        return [('Wearable', Wearable)]

    def lock_functions(self):
        return {
            'can_wear_wearables': lambda o, w: can_wear_wearables(w),
            'wearing': lambda o, w: can_wear_wearables(w) and o in w.wearing,
        }


class WearingFeature(Feature):
    """
    Provides object with tracking of what is worn.
    """
    wearing = []

    def __init__(self, *a, **kw):
        self._init_wearing()

    def _init_wearing(self):
        self.wearing = []

    @hook
    def server_started(self):
        """
        If this feature is added to a class that already has instances, we want
        to initialize those instances with our data.
        """
        if 'wearing' not in self.__dict__:
            self._init_wearing()

    @hook
    def desc_mod(self, desc, viewer):
        if not self.wearing:
            return desc
        names = map(lambda n: '{C%s{n' % n, viewer.list_of_names(self.wearing))
        return desc + '\nWearing: ' + utils.string.english_list(names)

    def wear(self, wearable):
        wearable = wearable.ref()
        wearable.move_to(self)
        self.wearing.append(wearable)
        wearable.on_wear(self)

    def unwear(self, wearable):
        wearable = wearable.ref()
        if wearable in self.wearing:
            self.wearing.remove(wearable)
        if wearable.is_worn_by(self):
            wearable.on_unwear()


class WearCmd(Command):
    """
    wear <wearable>

    Wears the indicated wearable object.
    """
    aliases = ('wear',)
    syntax = '<wearable>'
    arg_parsers = {
        'wearable': 'this'
    }
    lock = 'can_touch() and can_wear_wearables()'

    def run(self, this, actor, args):
        """
        @type this: L{Wearable}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        this._check_wear_status()
        if this.worn_by == actor:
            actor.tell('{yYou are already wearing {c', this, '{y.')
        elif this.worn_by is not None:
            actor.tell('{c', this, ' {yis worn by {c', this.worn_by, '{y.')
        else:
            actor.wear(this)


class UnwearCmd(Command):
    """
    unwear <wearable>

    Removes a wearable object.
    """
    aliases = ('unwear',)
    syntax = '<wearable>'
    arg_parsers = {
        'wearable': 'this',
    }
    lock = 'can_touch() and can_wear_wearables()'

    def run(self, this, actor, args):
        """
        @type this: L{Wearable}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        this._check_wear_status()
        if this.worn_by != actor:
            actor.tell('{yYou are not wearing {c', this, '{y.')
        else:
            actor.unwear(this)


class Wearable(Thing):
    """
    A generic wearable object.
    """
    worn_by = None
    public_commands = [WearCmd, UnwearCmd]
    messages = Messages({
        'wear': {
            'actor': 'You put on $this.',
            '*': '$actor puts on $this.'
        },
        'unwear': {
            'actor': 'You take $this off.',
            '*': '$actor takes $this off.'
        }
    })

    @property
    def is_worn(self):
        return self.worn_by is not None

    def _check_wear_status(self):
        try:
            if self.ref() not in self.worn_by.wearing:
                raise ValueError
            if self.worn_by is not None and self.location != self.worn_by:
                raise ValueError
        except (AttributeError, ValueError):
            wearer = self.worn_by
            self.worn_by = None
            if self.ref() in wearer.wearing:
                wearer.wearing.remove(self.ref())

    def is_worn_by(self, wearer):
        return wearer.ref() == self.worn_by.ref()

    def on_wear(self, wearer):
        """
        Called after a wearable has been worn by a wearer.
        """
        self.worn_by = wearer.ref()
        if wearer.isa(Object) and wearer.has_location:
            self.emit_message('wear', location=wearer.location, actor=wearer)

    def on_unwear(self):
        prev = self.worn_by
        self.worn_by = None
        if self.db.is_valid(prev, Object) and prev.has_location:
            self.emit_message('unwear', location=prev.location, actor=prev)

    def before_object_moved(self, moving_from, moving_to, by=None):
        self._check_wear_status()
        if self.is_worn:
            raise errors.MoveDenied(self.ref(), moving_from, moving_to,
                                    self.ref(),
                                    msg="%s is currently worn." % self.name)
