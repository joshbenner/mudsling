import logging
logger = logging.getLogger('pathfinder')
logger.info("Loading pathfinder...")

import os
import inflect
from pathfinder import Character

from pathfinder.extensibility import PathfinderPlugin
from pathfinder.objects import Thing
import pathfinder.languages
import pathfinder.data
import pathfinder.races
import pathfinder.skills  # Skills must come before feats.
import pathfinder.feats

inflection = inflect.engine()


class PathfinderCorePlugin(PathfinderPlugin):

    def plugins_loaded(self):
        register = pathfinder.data.add_classes
        register(pathfinder.languages.Language, pathfinder.languages)
        register(pathfinder.races.Race, pathfinder.races)
        register(pathfinder.skills.Skill, pathfinder.skills)
        register(pathfinder.feats.Feat, pathfinder.feats)

    def pathfinder_data_path(self):
        """
        The path to Pathfinder data files.
        """
        return os.path.join(self.info.path, 'data')

    def object_classes(self):
        return [
            ('pathfinder.Thing', Thing),
            ('pathfinder.Character', Character)
        ]
