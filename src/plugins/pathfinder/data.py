import inspect

from mudsling.utils.sequence import CaselessDict

registry = CaselessDict()


def get(class_name, id):
    if isinstance(class_name, type):
        class_name = class_name.__name__
    return registry[class_name][id]


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


def add_from(cls, module):
    to_add = []
    for val in module.__dict__.itervalues():
        if inspect.isclass(val) and issubclass(val, cls) and val != cls:
            to_add.append(val)
    add(cls, to_add)


class ForceSlotsMetaclass(type):
    def __new__(mcs, name, bases, dict):
        if '__slots__' not in dict:
            dict['__slots__'] = ()
        return type.__new__(mcs, name, bases, dict)
