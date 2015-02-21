import inspect

from mudsling.storage import StoredObject, PersistentSlots


class Event(object):
    obj = None
    originator = None

    def __init__(self, obj=None, originator=None, **kw):
        """
        :param obj: The object that hosts the event, if any.
        :param originator: The object/whatever that caused the event.
        :param kw: Any additional attributes to set on the event.
        """
        if obj is not None:
            self.obj = obj
        if originator is not None:
            self.originator = originator
        self.__dict__.update(kw)


def event_handler(types):
    """
    Decorator to identify a member of an EventResponder as an event handler.

    :param types: The event type to handle.
    :type types: type
    """
    types = types if isinstance(types, tuple) else (types,)

    def decorate(f):
        f.handles_event_types = types
        return f
    return decorate


class EventResponder(PersistentSlots):
    """
    Base class for objects that wish to be event responders.
    """
    __slots__ = ()

    event_handler_cache = {}

    def respond_to_event(self, event):
        for handler in self._event_handlers(event):
            handler(self, event)

    def delegate_event(self, event, delegates):
        """
        Utility method that can be used to have delegate responders build a set
        of responses. Useful for child implementations of respond_to_event.
        """
        for d in (d for d in delegates if isinstance(d, EventResponder)):
            d.respond_to_event(event)

    @classmethod
    def _event_handlers(cls, event):
        etype = type(event)
        if cls not in EventResponder.event_handler_cache:
            EventResponder.event_handler_cache[cls] = {}
        if etype not in EventResponder.event_handler_cache[cls]:
            def f(m):
                if inspect.ismethod(m):
                    for t in getattr(m, 'handles_event_types', ()):
                        if isinstance(event, t):
                            return True
            handlers = [f[1] for f in inspect.getmembers(cls, predicate=f)]
            EventResponder.event_handler_cache[cls][etype] = handlers
        return EventResponder.event_handler_cache[cls][etype]


class StaticEventResponder(EventResponder):
    __slots__ = ()

    @classmethod
    def respond_to_event(cls, event):
        for handler in cls._event_handlers(event):
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

    def _spawn_event(self, event, *a, **kw):
        """
        Spawn (if necessary) an event object based on the passed event or event
        class. Also sets event.obj if it's an Event subclass.

        Used by trigger_event().

        :param event: The event to trigger, or the event class to instantiate.
        :param a: Position arguments to pass to event instantiation.
        :param kw: Keyword arguments to pass to event instantiation.

        :return: The instantiated event, or the event that was passed in.
        """
        if inspect.isclass(event):
            event = event(*a, **kw)
        if isinstance(event, Event) and event.obj is None:
            if isinstance(self, StoredObject):
                event.obj = self.ref()
            else:
                event.obj = self
        return event

    def trigger_event(self, event, *a, **kw):
        """
        Trigger an event to be propagated to all responders.

        :param event: The event to trigger, or the event class to instantiate.
        :param a: Position arguments to pass to event instantiation.
        :param kw: Keyword arguments to pass to event instantiation.

        :return: The event.
        """
        event = self._spawn_event(event, *a, **kw)
        for r in self.event_responders(event):
            if isinstance(r, EventResponder) or issubclass(r, EventResponder):
                d = r.respond_to_event
                # noinspection PyUnresolvedReferences
                if (inspect.isfunction(d)
                        or (inspect.ismethod(d) and d.im_self is not None)):
                    d(event)
        return event

    def event_responders(self, event):
        """:rtype: list"""
        return []


class RespondsToOwnEvents(HasEvents, EventResponder):
    """
    An event-bearing object that can host its own handlers.
    """
    def event_responders(self, event):
        r = super(RespondsToOwnEvents, self).event_responders(event)
        # noinspection PyUnresolvedReferences
        r.append(self.ref() if isinstance(self, StoredObject) else self)
        return r
