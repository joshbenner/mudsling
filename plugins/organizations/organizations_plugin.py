"""
Organizations plugin.
"""

from mudsling.extensibility import GamePlugin

from organizations import *


class OrganizationsPlugin(GamePlugin):
    def object_classes(self):
        return [('Organization', Organization)]
