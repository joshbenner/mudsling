from mudsling.extensibility import GamePlugin

from pathfinder.objects import Thing


class PathfinderPlugin(GamePlugin):
    def object_classes(self):
        return [
            ('pathfinder.Thing', Thing),
        ]
