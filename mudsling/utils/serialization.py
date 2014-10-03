import json


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
