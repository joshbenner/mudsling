"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

import inspect

from .events import EventResponder, HasEvents


class Feature(EventResponder):
    """
    @cvar persistent: Persistent Features are stored on an object that
        HasFeatures, wheras non-persistent Features are applied and discarded.
    """
    __slots__ = ()

    name = ''
    description = ''
    modifiers = []
    persistent = True

    def __str__(self):
        return self.name

    def respond_to_event(self, event, responses):
        self.delegate_event(event, responses, self.modifiers)

    def apply_to(self, obj):
        pass


class HasFeatures(HasEvents):
    __slots__ = ('features',)

    def __init__(self, *a, **kw):
        # May not be last in MRO before object.
        super(HasFeatures, self).__init__(*a, **kw)
        self.features = []

    def event_responders(self, event):
        return list(self.features)

    def add_feature(self, feature):
        if inspect.isclass(feature):
            feature = feature()
        if not hasattr(self, 'features'):
            self.features = []
        if feature.persistent:
            self.features.append(feature)
        feature.apply_to(self)
