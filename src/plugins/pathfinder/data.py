from mudsling import pickler
from mudsling.utils.sequence import CaselessDict

registry = CaselessDict()


def get(class_name, id):
    return registry[class_name][id]


def add(class_name, obj):
    registry[class_name][obj.id] = obj


def loaded_data(clsname, parents, members):
    registry[clsname] = {}
    if 'id' not in members:
        members['id'] = ''
    members['persistent_id'] = staticmethod(lambda obj: obj.id)
    members['persistent_load'] = staticmethod(lambda id: registry[clsname][id])
    cls = type(clsname, parents, members)
    # noinspection PyUnresolvedReferences
    pickler.register_external_type(cls, cls.persistent_id, cls.persistent_load)
    return cls
