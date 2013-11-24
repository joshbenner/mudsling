import inspect
from collections import OrderedDict

import mudsling.storage
import mudsling.pickler

event_types = {}


class EventType(object):
    __slots__ = ('name',)

    def __new__(cls, name):
        return event_types.get(name, super(EventType, cls).__new__(cls))

    def __init__(self, name):
        self.name = name
        event_types[name] = self

    def __repr__(self):
        return "%s.%s('%s')" % (self.__class__.__module__,
                                self.__class__.__name__,
                                self.name)

    def __str__(self):
        return self.name


# Support storage of EventType in database by pickling only the name.
mudsling.pickler.register_external_type(EventType, lambda e: e.name, EventType)


class Event(object):
    obj = None

    def __init__(self, event_type, **kw):
        """
        :param event_type: The name/type of the event.
        :type event_type: str or EventType
        """
        self.type = event_type
        self.set_params(**kw)

    def set_params(self, **kw):
        self.__dict__.update(kw)

    # Legacy support for use of the name attribute.
    @property
    def name(self):
        return self.type

    @name.setter
    def name(self, val):
        self.type = val


class EventResponder(mudsling.storage.PersistentSlots):
    """
    Base class for objects that wish to be event responders.
    """
    __slots__ = ()

    event_callbacks = {}

    def respond_to_event(self, event, responses):
        """
        A responder should add their response(s) to the responses dictionary.
        """
        if event.name in self.event_callbacks:
            callback = self.event_callbacks[event.name]
            getattr(self, callback)(event, responses)

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

    def trigger_event(self, event, **kw):
        if isinstance(event, (EventType, basestring)):
            event = Event(event)
        event.set_params(**kw)
        event.obj = self
        responses = OrderedDict()
        for r in self.event_responders(event):
            if isinstance(r, EventResponder) or issubclass(r, EventResponder):
                d = r.respond_to_event
                if (inspect.isfunction(d)
                        or (inspect.ismethod(d) and d.im_self is not None)):
                    responses[r] = d(event, responses)
        event.responses = responses
        return event

    def event_responders(self, event):
        raise NotImplementedError("'%s' does not implement event_responders()"
                                  % self.__class__.__name__)
