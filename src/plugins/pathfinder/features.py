"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

from .events import EventResponder, HasEvents


class Feature(EventResponder):
    name = 'Unnamed Feature'
    effects = []

    def respond_to_event(self, event, responses, *a, **kw):
        self.delegate_event(event, responses, self.effects, *a, **kw)


class HasFeatures(HasEvents):
    features = []

    def event_responders(self, event):
        return self.features



