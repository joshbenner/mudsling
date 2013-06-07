import logging

from mudsling import pickler
from mudsling.utils.sequence import CaselessDict

registry = CaselessDict()
logger = logging.getLogger('pathfinder')


def get(class_name, id):
    return registry[class_name][id]


def add(class_name, obj):
    registry[class_name][obj.id] = obj


def loaded_data(clsname, parents, members):
    registry[clsname] = CaselessDict()

    if '__slots__' in members:
        if 'id' not in members['__slots__']:
            members['__slots__'] = list(members['__slots__'])
            members['__slots__'].append('id')
    elif 'id' not in members:
        members['id'] = ''

    members['persistent_id'] = staticmethod(lambda obj: obj.id)
    members['persistent_load'] = staticmethod(lambda id: get(clsname, id))
    cls = type(clsname, parents, members)
    # noinspection PyUnresolvedReferences
    pickler.register_external_type(cls, cls.persistent_id, cls.persistent_load)

    oldinit = members.get('__init__', None)

    def newinit(self, *a, **kw):
        self.id = ''
        for k, v in kw.iteritems():
            try:
                setattr(self, k, v)
            except AttributeError:
                continue
        if oldinit is not None:
            oldinit(self, *a, **kw)
        else:
            try:
                super(cls, self).__init__(*a, **kw)
            except TypeError:  # Don't die on __init__ param issues.
                pass
        logger.info("Loaded %s: %s" % (clsname, self.id))

    cls.__init__ = newinit

    return cls
