"""
Wearables plugin.
"""

from mudsling.extensibility import GamePlugin

from wearables import *


class WearablesPlugin(GamePlugin):
    def object_classes(self):
        return [('Wearable', Wearable)]

    def lock_functions(self):
        return {
            'can_wear_wearables': lambda o, w: can_wear_wearables(w),
            'wearing': lambda o, w: can_wear_wearables(w) and o in w.wearing,
        }
