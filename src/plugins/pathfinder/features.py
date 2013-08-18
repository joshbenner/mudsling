"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

import inspect

import mudsling.messages
import mudsling.storage
import mudsling.objects

import pathfinder.events
import pathfinder.data


class FeatureMetaClass(pathfinder.data.ForceSlotsMetaclass):
    def __str__(cls):
        return cls.name if hasattr(cls, 'name') else repr(cls)


class Feature(pathfinder.events.EventResponder, mudsling.messages.HasMessages):
    __metaclass__ = FeatureMetaClass

    feature_type = 'feature'
    name = ''
    description = ''
    modifiers = []

    def __str__(self):
        return self.name

    def respond_to_event(self, event, responses):
        pass

    def apply_to(self, obj):
        from .objects import is_pfobj
        if is_pfobj(obj):
            for mod in self.modifiers:
                obj.apply_effect(mod, source=self)
        self._show_msg(obj, 'apply')

    def remove_from(self, obj):
        from .objects import is_pfobj
        if is_pfobj(obj):
            obj.remove_effects_by_source(self)
        self._show_msg(obj, 'remove')

    def _show_msg(self, obj, msg):
        if (isinstance(obj, (mudsling.storage.ObjRef, mudsling.objects.Object))
                and obj.isa(mudsling.objects.Object)):
            msg = self.get_message(msg, feature=self, subject=obj)
            if msg:
                obj.emit(msg)


class HasFeatures(pathfinder.events.HasEvents):
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
