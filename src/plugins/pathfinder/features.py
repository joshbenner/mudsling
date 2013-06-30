"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

import inspect

from .events import EventResponder, HasEvents
from .data import ForceSlotsMetaclass


class FeatureMetaClass(ForceSlotsMetaclass):
    def __str__(cls):
        return cls.name if hasattr(cls, 'name') else repr(cls)


class Feature(EventResponder):
    __metaclass__ = FeatureMetaClass

    name = ''
    description = ''

    def __str__(self):
        return self.name

    def respond_to_event(self, event, responses):
        pass

    def apply_to(self, obj):
        pass

    def remove_from(self, obj):
        pass


class CharacterFeature(Feature):
    modifiers = []

    def apply_to(self, obj):
        from .characters import is_pfchar
        if is_pfchar(obj):
            for mod in self.modifiers:
                obj.apply_effect(mod, source=self)

    def remove_from(self, obj):
        from .characters import is_pfchar
        if is_pfchar(obj):
            obj.remove_effects_by_source(self)


class HasFeatures(HasEvents):
    _features = []

    def __init__(self, *a, **kw):
        # May not be last in MRO before object.
        super(HasFeatures, self).__init__(*a, **kw)
        self._features = []

    @property
    def features(self):
        return self._features

    def event_responders(self, event):
        return list(self.features)

    def add_feature(self, feature):
        if inspect.isclass(feature):
            feature = feature()
        if '_features' not in self.__dict__:
            self._features = []
        self._features.append(feature)
        feature.apply_to(self)
        return feature

    def remove_feature(self, feature):
        if inspect.isclass(feature):
            for f in self._features:
                if isinstance(f, feature):
                    feature = f
                    break
        if feature in self._features:
            self._features.remove(feature)
            feature.remove_from(self)
        return feature
