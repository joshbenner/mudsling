import copy
import json
import jsonpath_rw.parser

_jsonpath = jsonpath_rw.parser.JsonPathParser()
_jsonpath_cache = {}


def jsonpath(path):
    if path not in _jsonpath_cache:
        _jsonpath_cache[path] = _jsonpath.parse(path)
    return _jsonpath_cache[path]


def json_decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = json_decode_list(item)
        elif isinstance(item, dict):
            item = json_decode_dict(item)
        rv.append(item)
    return rv


def json_decode_dict(data, dict_cls=dict):
    rv = dict_cls()
    for key, value in data if isinstance(data, list) else data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = json_decode_list(value)
        elif isinstance(value, dict):
            value = json_decode_dict(value)
        rv[key] = value
    return rv


def json_load_ascii(text):
    return json.JSONDecoder(object_pairs_hook=json_decode_dict).decode(text)


class JSONMappable(object):
    """
    A mixin class to allow another class to load/save to/from JSON.

    :cvar json_map: Maps instance attributes to JSONPath representations.
    :type json_map: dict

    :cvar json_blank: What a blank JSON-version of this object looks like.
    :type json_blank: dict
    """
    json_map = {}
    json_blank = {}

    def load_from_json_file(self, filepath):
        with open(filepath) as f:
            content = f.read()
        return self.from_json(content)

    def from_json(self, text):
        return self.from_json_data(json_load_ascii(text))

    def from_json_data(self, json_data):
        for attr, path in self.json_map.iteritems():
            json_values = jsonpath(path).find(json_data)
            if len(json_values):
                # Only use first value. If you need list, map to it.
                setattr(self, attr, json_values[0].value)

    def to_json(self):
        json_data = copy.deepcopy(self.json_blank)
        for attr, path in self.json_map.iteritems():
            jsonpath(path).update(json_data, getattr(self, attr))
        return json_data
