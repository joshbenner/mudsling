import os
import inflect

from pathfinder.extensibility import PathfinderPlugin
from pathfinder.objects import Thing, Character
import pathfinder.data
import pathfinder.races
import pathfinder.skills
import pathfinder.feats

inflection = inflect.engine()


class PathfinderCorePlugin(PathfinderPlugin):

    def plugins_loaded(self):
        pathfinder.data.add_from(pathfinder.races.Race, pathfinder.races)
        pathfinder.data.add_from(pathfinder.skills.Skill, pathfinder.skills)
        pathfinder.data.add_from(pathfinder.feats.Feat, pathfinder.feats)

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
