import logging
logger = logging.getLogger('pathfinder')
logger.info("Loading pathfinder...")

import os

import pathfinder
import pathfinder.extensibility
import pathfinder.objects
import pathfinder.characters
import pathfinder.languages
import pathfinder.races
import pathfinder.skills  # Skills must come before feats.
import pathfinder.feats
import pathfinder.special_abilities
import pathfinder.conditions
import pathfinder.classes


class PathfinderCorePlugin(pathfinder.extensibility.PathfinderPlugin):

    def server_startup(self):
        if self.options is not None:
            pathfinder.config.update(self.options)

    def plugins_loaded(self):
        register = pathfinder.data.add_classes
        register(pathfinder.languages.Language, pathfinder.languages)
        register(pathfinder.races.Race, pathfinder.races)
        register(pathfinder.skills.Skill, pathfinder.skills)
        register(pathfinder.feats.Feat, pathfinder.feats)
        register(pathfinder.feats.Feat, pathfinder.special_abilities,
                 exclude=(pathfinder.special_abilities.SpecialAbility,))
        register(pathfinder.conditions.Condition, pathfinder.conditions)
        register(pathfinder.classes.Class, pathfinder.classes)

    def pathfinder_data_path(self):
        """
        The path to Pathfinder data files.
        """
        return os.path.join(self.info.path, 'data')

    def object_classes(self):
        return [
            ('PF Thing', pathfinder.objects.Thing),
            ('PF Character', pathfinder.characters.Character)
        ]
