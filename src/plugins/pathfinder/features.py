"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

from .events import EventResponder, HasEvents


class Feature(EventResponder):
    __slots__ = ()

    name = ''
    description = ''
    modifiers = []

    def __str__(self):
        return self.name

    def respond_to_event(self, event, responses):
        self.delegate_event(event, responses, self.modifiers)


class HasFeatures(HasEvents):
    __slots__ = ('features',)

    def __init__(self, *a, **kw):
        # May not be last in MRO before object.
        super(HasFeatures, self).__init__(*a, **kw)
        self.features = []

    def event_responders(self, event):
        return list(self.features)
