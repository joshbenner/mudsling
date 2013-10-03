"""
Wearables plugin.
"""

from mudsling.extensibility import GamePlugin
from mudslingcore.objects import Character

from wearables import *


class WearablesPlugin(GamePlugin):
    def server_startup(self):
        Character.add_class_mixin(WearingMixin)

    def object_classes(self):
        return [('Wearable', Wearable)]

    def lock_functions(self):
        return {
            'can_wear_wearables': lambda o, w: can_wear_wearables(w),
            'wearing': lambda o, w: can_wear_wearables(w) and o in w.wearing,
        }
