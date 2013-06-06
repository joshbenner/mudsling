from collections import OrderedDict

from .features import Feature
from .sizes import size_categories
from .data import loaded_data


class RacialTrait(Feature):
    pass


class Race(Feature):
    __metaclass__ = loaded_data
    __slots__ = ('id', 'singular', 'plural', 'physical_description',
                 'society', 'relations', 'size', 'racial_traits')

    # Init runs with data already loaded into members.
    def __init__(self, *a, **kw):  # Metaclass processes keyword args.
        super(Race, self).__init__(self.name)
        if not self.id:
            self.id = self.singular
        if isinstance(self.size, basestring):
            if self.size in size_categories:
                self.size = size_categories[self.size]
        self._process_racial_traits()

    def __repr__(self):
        return "pathfinder.race('%s')" % (self.id or self.singular)

    def __str__(self):
        return self.singular

    @property
    def name(self):
        return self.singular

    @name.setter
    def name(self, val):
        self.singular = val

    def respond_to_event(self, event, responses):
        self.delegate_event(event, responses, self.racial_traits)

    def _process_racial_traits(self):
        raw = self.racial_traits
        traits = OrderedDict()
        for name, info in raw.iteritems():
            desc, effects = info
            trait = RacialTrait(name, desc)
            trait.effects = effects
            traits[name] = trait
        self.racial_traits = traits
