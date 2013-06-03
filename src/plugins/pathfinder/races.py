from collections import OrderedDict

from mudsling import pickler

from .features import Feature
from .sizes import size_categories

races = {}


def add(race):
    races[race.id.lower()] = race


def get(race_id):
    return races[race_id.lower()]


class RacialTrait(Feature):
    pass


class Race(Feature):
    # name, description from Feature
    id = ''
    singular = ''
    plural = ''
    physical_description = ''
    society = ''
    relations = ''
    size = size_categories['medium']
    racial_traits = []
    initialized = False

    @staticmethod
    def pickle_id(race):
        return race.singular

    @staticmethod
    def pickle_load(id):
        return get(id)

    def __new__(cls, *args, **kwargs):
        if args:
            return get(args[0])
        else:
            return super(Race, cls).__new__(cls, *args, **kwargs)

    # noinspection PyUnusedLocal
    def __init__(self, *a, **kw):
        # Keep *a here so that calling __init__ on existing instance works.
        if not self.initialized:
            super(Race, self).__init__('Race %s' % id(self))
            self.__dict__.update(kw)
            if not self.id:
                self.id = self.singular.lower()
            self._process_racial_traits()
            self.initialized = True

    def __repr__(self):
        return "pathfinder.Race('%s')" % (self.id or self.singular)

    def __str__(self):
        return self.singular

    @property
    def name(self):
        return self.singular

    @name.setter
    def name(self, val):
        self.singular = val

    def respond_to_event(self, event, responses, *a, **kw):
        self.delegate_event(event, responses, self.racial_traits, *a, **kw)

    def _process_racial_traits(self):
        if self.initialized:
            return
        raw = self.racial_traits
        traits = OrderedDict()
        for name, info in raw.iteritems():
            desc, effects = info
            trait = RacialTrait(name, desc)
            trait.effects = effects
            traits[name] = trait
        self.racial_traits = traits

pickler.register_external_type(Race, Race.pickle_id, Race.pickle_load)
