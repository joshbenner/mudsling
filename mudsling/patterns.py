"""
Patterns are configuration that describe default values for object instances.

Patterns provide default attribute values. This is a way to have configuration
describe data-only differences between different incarnations of a more general
class. This also lets you keep information that's more specific than shared
functionality separate from your Python code.

Example:
* Class: d20.weapons.Sword
* Pattern: "Katana" described in katana.json
* Instance: "Katana" of class d20.weapons.Sword of pattern "Katana"
"""
import os
import fnmatch
import logging
import json
import collections

from mudsling.utils.modules import class_from_path


class PatternError(Exception):
    pass


class PatternManager(object):
    """
    Loads all pattern files and prepares them for use by object instances.

    @ivar patterns: Key/val store of pattern ids and patterns.
    @type patterns: dict
    """
    patterns = None

    def __init__(self, plugins):
        """
        Create a new PatternManager and load all patterns in activated plugins
        found within the passed PluginManager.

        @param plugins: The plugin manager whose patterns to load.
        @type plugins: mudsling.extensibility.PluginManager
        """
        self.patterns = {}

        # Build the list of pattern directories.
        dirs = []
        for info in plugins.active_plugins("GamePlugin"):
            dirs.extend(info.plugin_object.pattern_paths())
        logging.debug("Pattern paths: %r" % dirs)

        for dir in dirs:
            for root, dirnames, filenames in os.walk(dir):
                for filename in fnmatch.filter(filenames, '*.json'):
                    p = self.load_pattern_from_file(os.path.join(root,
                                                                 filename))
                    if isinstance(p, Pattern):
                        self.register_pattern(p)

    def register_pattern(self, pattern, id=None):
        """
        Register a pattern object to the PatternManager.

        @param pattern: The pattern to register
        @type pattern: Pattern

        @param id: The id key to identify the pattern with. Defaults to the
            id within the pattern.
        @type id: str
        """
        self.patterns[id or pattern.id] = pattern

    def load_pattern_from_file(self, filepath):
        try:
            with open(filepath, '') as file:
                data = json.load(file,
                                 object_pairs_hook=collections.OrderedDict)
            if not isinstance(data, dict):
                raise Exception("Pattern JSON root must be an object.")
            # If no id specified, default to filename before '.json'
            if 'id' not in data:
                data['id'] = os.path.basename(filepath).rstrip('.json')
            return Pattern(data)
        except Exception:
            logging.exception("Error loading pattern at: %s" % filepath)
            return


class Pattern(object):
    """
    Class to hold pattern data.

    @ivar id: The unique identifier of the pattern.
    @type id: str

    @ivar name: The name that objects of this pattern will likely receive.
    @type name: str

    @ivar cls: The class associated with this pattern.
    @type cls: type

    @ivar attributes: The data defaults for this pattern.
    @type attributes: dict

    @ivar data: Original copy of the data used to create the Pattern object.
        Useful for accessing additional metadata about the pattern.
    @type data: dict
    """
    # Data validation.
    _required = ('id', 'name', 'class')
    _valid_types = {
        'id': (basestring,),
        'name': (basestring,),
        'class': (basestring, type),
        'attributes': (dict,)
    }

    id = ''
    name = ''
    cls = None
    attributes = {}
    data = {}

    def __init__(self, data):
        """
        Pattern data format:
        {
            "id": "unique_id",
            "name": "Instance Name",
            "class": "module.path.to.Class",
            "attributes": {
                "foo": <value>,
                ...,
                "attrN": <value>
            }
            ... arbitrary metadata key/vals ...
        }

        @param data: dict of pattern data.
        @type data: dict
        """
        self.validate_data(data)
        self.data = data
        self.id = data['id']
        self.name = data['name']
        self.attributes = data['attributes'] if 'attributes' in data else {}
        if isinstance(data['class'], basestring):
            self.cls = class_from_path(data['class'])
        else:  # Must be a child of type.
            self.cls = data['class']

    def validate_data(self, data):
        for req in self._required:
            if req not in data:
                msg = "Invalid pattern. Missing required key: %s" % req
                raise PatternError(msg)
        for key, valTypes in self._valid_types.iteritems():
            if key in data:
                rightType = False
                for valType in valTypes:
                    if isinstance(data[key], valType):
                        rightType = True
                        break
                if not rightType:
                    names = []
                    for valType in valTypes:
                        name = ''
                        if valType.__module__ is not '__builtin__':
                            name += valType.__module__ + '.'
                        name += valType.__name__
                        names.append(name)
                    names = ' or '.join(names)
                    msg = "Invalid pattern. Key %r must be of type %s"
                    raise PatternError(msg % (key, names))
