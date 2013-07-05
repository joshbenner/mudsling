import inspect
from collections import OrderedDict

from mudsling.storage import PersistentSlots


class Event(object):
    obj = None

    def __init__(self, name, **kw):
        self.name = name
        self.__dict__.update(kw)


class EventResponder(PersistentSlots):
    """
    Base class for objects that wish to be event responders.
    """
    __slots__ = ()

    def respond_to_event(self, event, responses):
        """
        A responder should add their response(s) to the responses dictionary.
        """
        raise NotImplementedError("'%s' does not implement respond_to_event()"
                                  % self.__class__.__name__)

    def delegate_event(self, event, responses, delegates):
        """
        Utility method that can be used to have delegate responders build a set
        of responses. Useful for child implementations of respond_to_event.
        """
        sub_responses = OrderedDict()
        for d in (d for d in delegates if isinstance(d, EventResponder)):
            sub_responses[d] = d.respond_to_event(event, responses)
        responses.update(sub_responses)


class HasEvents(object):
    """
    An object that can notify other objects of arbitrary events.
    """

    def __init__(self, *a, **kw):
        try:
            # noinspection PyArgumentList
            super(HasEvents, self).__init__(*a, **kw)
        except TypeError:
            # If we are last in MRO before object, then we may hit this, but it
            # is harmless.
            pass

    def trigger_event(self, event):
        event.obj = self
        responses = OrderedDict()
        for r in self.event_responders(event):
            if isinstance(r, EventResponder) or issubclass(r, EventResponder):
                d = r.respond_to_event
                if (inspect.isfunction(d)
                        or (inspect.ismethod(d) and d.im_self is not None)):
                    responses[r] = d(event, responses)
        return responses

    def event_responders(self, event):
        raise NotImplementedError("'%s' does not implement event_responders()"
                                  % self.__class__.__name__)
