from mudsling.commands import Command
from mudsling.messages import Messages
from mudsling.objects import Object
from mudsling import errors

from mudsling import utils
import mudsling.utils.string

import mudslingcore.objects


def can_wear_wearables(who):
    return who.isa(Wearer)


class WearablesError(errors.Error):
    pass


class CannotWearError(WearablesError):
    pass


class AlreadyWearingError(CannotWearError):
    pass


class NotWearingError(WearablesError):
    pass


class Wearer(mudslingcore.objects.DescribableObject):
    """
    Provides object with tracking of what is worn.
    """
    wearing = []

    def on_object_created(self):
        super(Wearer, self).on_object_created()
        self._init_wearing()

    def _init_wearing(self):
        self.wearing = []

    def server_started(self):
        """
        If this feature is added to a class that already has instances, we want
        to initialize those instances with our data.
        """
        if 'wearing' not in self.__dict__:
            self._init_wearing()

    def describe_to(self, viewer):
        desc = super(Wearer, self).describe_to(viewer)
        if not self.wearing:
            return desc
        names = map(lambda n: '{C%s{n' % n, viewer.list_of_names(self.wearing))
        return desc + '\nWearing: ' + utils.string.english_list(names)

    def wear(self, wearable):
        wearable = wearable.ref()
        wearable.before_wear(self)
        wearable.move_to(self)
        self.wearing.append(wearable)
        wearable.on_wear(self)

    def unwear(self, wearable):
        wearable = wearable.ref()
        if wearable in self.wearing:
            wearable.before_unwear(self)
            self.wearing.remove(wearable)
        if not wearable.is_worn_by(self):
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
        this.check_wear_status()
        try:
            actor.wear(this)
        except AlreadyWearingError:
            actor.tell('{yYou are already wearing {c', this, '{y.')
        except CannotWearError as e:
            if e.message:
                actor.tell('{y', e.message)
            elif this.worn_by is not None:
                actor.tell('{c', this, ' {yis worn by {c', this.worn_by, '{y.')
            else:
                actor.tell('{yYou cannot wear {c', this, '{y.')
        except WearablesError as e:
            if e.message:
                actor.tell('{y', e.message)
            else:
                actor.tell('{yYou cannot wear {c', this, '{y.')


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
        this.check_wear_status()
        try:
            actor.unwear(this)
        except NotWearingError:
            actor.tell('{yYou are not wearing {c', this, '{y.')
        except WearablesError as e:
            if e.message:
                actor.tell('{y', e.message)
            else:
                actor.tell('{yYou cannot unwear {c', this, '{y.')


class Wearable(mudslingcore.objects.Thing):
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

    def check_wear_status(self):
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

    def before_wear(self, wearer):
        wearer = wearer.ref()
        if self.worn_by == wearer:
            raise AlreadyWearingError()
        elif self.is_worn:
            raise CannotWearError()

    def on_wear(self, wearer):
        """
        Called after a wearable has been worn by a wearer.
        """
        self.worn_by = wearer.ref()
        if wearer.isa(Object) and wearer.has_location:
            self.emit_message('wear', location=wearer.location, actor=wearer)

    def before_unwear(self, wearer):
        if self.worn_by != wearer.ref():
            raise NotWearingError()

    def on_unwear(self):
        prev = self.worn_by
        self.worn_by = None
        if self.db.is_valid(prev, Object) and prev.has_location:
            self.emit_message('unwear', location=prev.location, actor=prev)

    def before_object_moved(self, moving_from, moving_to, by=None, via=None):
        self.check_wear_status()
        if self.is_worn:
            if by == self.worn_by:
                msg = "You must unwear %s before discarding it."
                msg = msg % by.name_for(self)
            else:
                msg = "%s is currently worn." % self.name
            raise errors.MoveDenied(self.ref(), moving_from, moving_to,
                                    self.ref(), msg=msg)
