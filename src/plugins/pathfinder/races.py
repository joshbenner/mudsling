from mudsling import pickler

from .features import Feature
from .sizes import size_categories

races = {}


def add(race):
    races[race.id.lower()] = race


def get(race_id):
    return races[race_id.lower()]


class Race(Feature):
    id = ''
    singular = ''
    plural = ''
    description = ''
    physical_description = ''
    society = ''
    relations = ''
    size = size_categories['medium']
    racial_traits = []

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
        self.__dict__.update(kw)
        if not self.id:
            self.id = self.singular.lower()

    def __repr__(self):
        return "%s Race" % self.singular

    @property
    def name(self):
        return self.singular

    def respond_to_event(self, event, responses, *a, **kw):
        self.delegate_event(event, responses, self.racial_traits, *a, **kw)

pickler.register_external_type(Race, Race.pickle_id, Race.pickle_load)
