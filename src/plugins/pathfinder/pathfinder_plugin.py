import logging
from pathfinder.things import Thing

logger = logging.getLogger('pathfinder')
logger.info("Loading pathfinder...")

import os

import pathfinder
import pathfinder.extensibility
import pathfinder.characters
import pathfinder.topography


class PathfinderCorePlugin(pathfinder.extensibility.PathfinderPlugin):

    def __init__(self, game, info, manager):
        super(PathfinderCorePlugin, self).__init__(game, info, manager)
        # Register the PathfinderPlugin type of plugin.
        manager.PLUGIN_CATEGORIES['PathfinderPlugin'] \
            = pathfinder.extensibility.PathfinderPlugin

    def server_startup(self):
        if self.options is not None:
            pathfinder.config.update(self.options)

    def plugins_loaded(self):
        pf_plugins = self.game.plugins.active_plugins('PathfinderPlugin')
        for plugin in pf_plugins:
            plugin.register_pathfinder_data()
        pathfinder.data_loaded = True

    def pathfinder_data_path(self):
        """
        The path to Pathfinder data files.
        """
        return os.path.join(self.info.path, 'data')

    def object_classes(self):
        return [
            ('PF Thing', Thing),
            ('PF Character', pathfinder.characters.Character),
            ('PF Room', pathfinder.topography.Room)
        ]
