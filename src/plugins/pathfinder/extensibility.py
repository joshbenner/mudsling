import os

from mudsling.extensibility import GamePlugin


class PathfinderPlugin(GamePlugin):
    """
    Plugins of this type can provide Pathfinder data. Technically, any
    GamePlugin instance may provide Pathfinder data, but this class makes it a
    little easier.
    """
    def pathfinder_data_path(self):
        """
        The path to Pathfinder data files.
        """
        return self.info.path
