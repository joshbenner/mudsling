from collections import OrderedDict


class Event(object):
    def __init__(self, name, **kw):
        self.name = name
        self.__dict__.update(kw)


class EventResponder(object):
    """
    Base class for objects that wish to be event responders.
    """
    __slots__ = ()

    def respond_to_event(self, event, responses):
        raise NotImplementedError("'%s' does not implement respond_to_event()"
                                  % self.__class__.__name__)

    def delegate_event(self, event, responses, delegates):
        sub_responses = {}
        for d in (d for d in delegates if isinstance(d, EventResponder)):
            sub_responses[d] = d.respond_to_event(event, responses)
        responses.update(sub_responses)


class HasEvents(object):
    """
    An object that can notify other objects of arbitrary events.
    """
    __slots__ = ()

    def trigger_event(self, event):
        responses = OrderedDict()
        for r in self.event_responders(event):
            if isinstance(r, EventResponder):
                responses[r] = r.respond_to_event(event, responses)
        return responses

    def event_responders(self, event):
        raise NotImplementedError("'%s' does not implement event_responders()"
                                  % self.__class__.__name__)
