import os
import json
import inflect

from pathfinder.extensibility import PathfinderPlugin
from pathfinder.objects import Thing, Character
from pathfinder import races

inflection = inflect.engine()


class PathfinderCorePlugin(PathfinderPlugin):
    def plugins_loaded(self):
        self._load_data()

    def object_classes(self):
        return [
            ('pathfinder.Thing', Thing),
            ('pathfinder.Character', Character)
        ]

    def _find_data_files(self, path):
        allfiles = []
        for dirname, dirnames, files in os.walk(path):
            allfiles.extend([os.path.join(dirname, f) for f in files
                             if f.endswith('.json')])
        return allfiles

    def _load_data(self):
        responses = self.game.invoke_hook('pathfinder_data_path')
        for dir in ('races',):
            fname = "_load_%s" % inflection.singular_noun(dir)
            for module, path in responses.iteritems():
                path = os.path.join(path, dir)
                if os.path.isdir(path):
                    for filepath in self._find_data_files(path):
                        with open(filepath, 'r') as file:
                            data = json.load(file)
                            getattr(self, fname)(data)

    def _load_race(self, data):
        races.add(races.Race(**data))
