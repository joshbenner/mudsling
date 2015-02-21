import inspect

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

    def is_type(self, event_type):
        """
        Determine if this event is of a given type.

        :param event_type: The event type to inquire about. Can be a string or
            an EventType instance, and the method will resolve everything for
            comparison.
        :type event_type: str or EventType

        :rtype: bool
        """
        if isinstance(event_type, EventType):
            event_type = event_type.name
        if isinstance(self.type, EventType):
            my_type = self.type.name
        else:
            my_type = self.type
        return event_type.lower() == my_type.lower()


def event_handler(event_type):
    """
    Decorator to identify a member of an EventResponder as an event handler.

    :param event_type: The event type to handle.
    :type event_type: EventType
    """
    def decorate(f):
        if isinstance(event_type, EventType):
            f.handle_event = event_type.name
        else:
            f.handle_event = event_type
        return f
    return decorate


class EventResponder(mudsling.storage.PersistentSlots):
    """
    Base class for objects that wish to be event responders.
    """
    __slots__ = ()

    event_handlers = {}

    def respond_to_event(self, event):
        event_type = (event.type.name if isinstance(event.type, EventType)
                      else event.name)
        for handler in self._event_handlers(event_type):
            handler(self, event)

    def delegate_event(self, event, delegates):
        """
        Utility method that can be used to have delegate responders build a set
        of responses. Useful for child implementations of respond_to_event.
        """
        for d in (d for d in delegates if isinstance(d, EventResponder)):
            d.respond_to_event(event)

    @classmethod
    def _event_handlers(cls, etype):
        if cls not in EventResponder.event_handlers:
            EventResponder.event_handlers[cls] = {}
        if etype not in EventResponder.event_handlers[cls]:
            f = lambda m: (inspect.ismethod(m)
                           and getattr(m, 'handle_event', None) == etype)
            handlers = [f[1] for f in inspect.getmembers(cls, predicate=f)]
            EventResponder.event_handlers[cls][etype] = handlers
        return EventResponder.event_handlers[cls][etype]


class StaticEventResponder(EventResponder):
    __slots__ = ()

    @classmethod
    def respond_to_event(cls, event):
        event_type = (event.type.name if isinstance(event.type, EventType)
                      else event.name)
        for handler in cls._event_handlers(event_type):
            handler(event)


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
        for r in self.event_responders(event):
            if isinstance(r, EventResponder) or issubclass(r, EventResponder):
                d = r.respond_to_event
                if (inspect.isfunction(d)
                        or (inspect.ismethod(d) and d.im_self is not None)):
                    d(event)
        return event

    def event_responders(self, event):
        raise NotImplementedError("'%s' does not implement event_responders()"
                                  % self.__class__.__name__)
