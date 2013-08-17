import inspect

from mudsling.utils.sequence import CaselessDict
from mudsling import errors

from pathfinder.errors import DataNotFound

registry = CaselessDict()


def get(class_name, id):
    if isinstance(class_name, type):
        class_name = class_name.__name__
    try:
        return registry[class_name][id]
    except KeyError:
        raise DataNotFound("%s '%s' not found" % (class_name, id))


def add(class_name, obj):
    if isinstance(class_name, type):
        class_name = class_name.__name__
    if class_name not in registry:
        registry[class_name] = CaselessDict()
    if isinstance(obj, list) or isinstance(obj, tuple):
        for o in obj:
            add(class_name, o)
    else:
        registry[class_name][obj.name] = obj


def names(class_name):
    return registry[class_name].keys()


def all(class_name):
    return registry[class_name].values()


def __data_type_key(dt):
    if isinstance(dt, basestring):
        return str(dt).lower()
    elif inspect.isclass(dt):
        return dt.__name__.lower()
    else:
        return dt.__class__.__name__.lower()


def match(name, types=None, multiple=False, exact=True):
    # Match is done against CaselessDict, so name's case doesn't matter. But,
    # if we are doing a non-exact match, we will be checking .startswith().
    if not exact:
        name = name.lower()
    partial_matches = []
    exact_matches = []
    types = [__data_type_key(o) for o in (types or registry.iterkeys())]
    for data in (registry[clsname] for clsname in registry
                 if clsname.lower() in types):
        if name in data:
            exact_matches.append(data[name])
        elif not exact and not len(exact_matches):
            for d in data.keyList:
                if d.startswith(name):
                    partial_matches.append(data[d])

    matches = exact_matches or partial_matches

    if multiple:
        return matches
    elif len(matches) > 1:
        raise errors.AmbiguousMatch()
    elif len(matches) > 0:
        return matches[0]
    else:
        raise errors.FailedMatch()


def add_classes(cls, module, exclude=()):
    to_add = []
    excl = list(exclude)
    excl.append(cls)
    for val in module.__dict__.itervalues():
        if inspect.isclass(val) and issubclass(val, cls) and val not in excl:
            to_add.append(val)
    add(cls, to_add)


class ForceSlotsMetaclass(type):
    def __new__(mcs, name, bases, dict):
        if '__slots__' not in dict:
            dict['__slots__'] = ()
        return type.__new__(mcs, name, bases, dict)
