"""
Features decorate other objects. They primarily provide effects, though the
presence of a Feature at all can be meaningful (ie: check for existence of a
specific Feature).

Features are also designed to respond to events on HasEvents objects.
"""

from .events import EventResponder, HasEvents


class Feature(EventResponder):
    name = 'Unnamed Feature'
    description = ''
    effects = []

    def __init__(self, name, desc=''):
        self.name = name
        self.description = desc

    def respond_to_event(self, event, responses):
        self.delegate_event(event, responses, self.effects)


class HasFeatures(HasEvents):
    features = []

    def event_responders(self, event):
        return self.features
