import os
import json
import inflect
import csv

from pathfinder.extensibility import PathfinderPlugin
from pathfinder.objects import Thing, Character
from pathfinder.races import Race
from pathfinder.skills import Skill
import pathfinder.data

inflection = inflect.engine()


class PathfinderCorePlugin(PathfinderPlugin):
    json_dirs = {
        Race: 'races',
    }
    csv_files = {
        Skill: 'skills',
    }

    def plugins_loaded(self):
        self._load_data()

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

    def _find_data_files(self, path):
        allfiles = []
        for dirname, dirnames, files in os.walk(path):
            allfiles.extend([os.path.join(dirname, f) for f in files
                             if f.endswith('.json')])
        return allfiles

    def _load_data(self):
        responses = self.game.invoke_hook('pathfinder_data_path')
        sniffer = csv.Sniffer()
        for cls, csvfile in self.csv_files.iteritems():
            for module, path in responses.iteritems():
                filepath = os.path.join(path, csvfile + '.csv')
                with open(filepath, 'Ub') as file:
                    dialect = sniffer.sniff(file.read(1024))
                    file.seek(0)
                    for line in csv.DictReader(file, dialect=dialect):
                        pathfinder.data.add(cls.__name__.lower(), cls(**line))

        for cls, dir in self.json_dirs.iteritems():
            for module, path in responses.iteritems():
                path = os.path.join(path, dir)
                if os.path.isdir(path):
                    for filepath in self._find_data_files(path):
                        with open(filepath, 'r') as file:
                            data = json.load(file)
                            pathfinder.data.add(cls.__name__.lower(),
                                                cls(**data))
