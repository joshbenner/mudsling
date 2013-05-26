"""
Wearables plugin.
"""

from mudsling.extensibility import GamePlugin
from mudsling.composition import hook, Feature, Featurized
from mudsling.commands import Command

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


class Wearable(Thing):
    """
    A generic wearable object.
    """
    worn_by = None

    def _check_wear_status(self):
        raise NotImplemented
