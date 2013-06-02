from collections import OrderedDict


class EventResponder(object):
    """
    Base class for objects that wish to be event responders.
    """
    def respond_to_event(self, event, responses, *a, **kw):
        raise NotImplementedError("'%s' does not implement respond_to_event()"
                                  % self.__class__.__name__)

    def delegate_event(self, event, responses, delegates, *a, **kw):
        sub_responses = {}
        for d in (d for d in delegates if isinstance(d, EventResponder)):
            sub_responses[d] = d.respond_to_event(event, responses, *a, **kw)
        responses.update(sub_responses)


class HasEvents(object):
    """
    An object that can notify other objects of arbitrary events.
    """
    def trigger_event(self, event, *a, **kw):
        responses = OrderedDict()
        for r in self.event_responders(event):
            if isinstance(r, EventResponder):
                responses[r] = r.respond_to_event(event, responses, *a, **kw)
        return responses

    def event_responders(self, event):
        raise NotImplementedError("'%s' does not implement event_responders()"
                                  % self.__class__.__name__)
