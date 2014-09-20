"""
Organizations plugin.
"""

from mudsling.extensibility import GamePlugin
from mudslingcore.globalvars import global_handlers

from organizations import *

global_handlers['org'] = lambda r, n: r.match_obj_of_type(n, cls=Organization)


class OrganizationsPlugin(GamePlugin):
    def object_classes(self):
        return [('Organization', Organization)]
