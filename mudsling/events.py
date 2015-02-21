import inspect

import zope.interface


class IEvent(zope.interface.Interface):
    obj = zope.interface.Attribute("The host object")


# noinspection PyMethodParameters
class IEventResponder(zope.interface.Interface):
    def respond_to_event(event):
        """Respond to the passed event."""


# noinspection PyMethodParameters
class IEventHost(zope.interface.Interface):
    def trigger_event(event, *a, **kw):
        """Trigger an event with optional parameters."""


class Event(object):
    zope.interface.implements(IEvent)
    
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


class EventResponder(object):
    """
    Base class for objects that wish to be event responders.
    """
    zope.interface.implements(IEventResponder)
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
        for d in (d for d in delegates if IEventResponder.providedBy(d)):
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
    zope.interface.classProvides(IEventResponder)

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Cannot instantiate static class.')

    @classmethod
    def respond_to_event(cls, event):
        for handler in cls._event_handlers(event):
            handler(event)


class HasEvents(object):
    """
    An object that can notify other objects of arbitrary events.
    """
    zope.interface.implements(IEventHost)

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
        if IEvent.providedBy(event) and event.obj is None:
            from mudsling.storage import StoredObject
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
            if IEventResponder.providedBy(r):
                r.respond_to_event(event)
        return event

    def event_responders(self, event):
        """:rtype: list"""
        return []


class RespondsToOwnEvents(HasEvents, EventResponder):
    """
    An event-bearing object that can host its own handlers.
    """
    def event_responders(self, event):
        from mudsling.storage import StoredObject
        r = super(RespondsToOwnEvents, self).event_responders(event)
        # noinspection PyUnresolvedReferences
        r.append(self.ref() if isinstance(self, StoredObject) else self)
        return r


class HasSubscribableEvents(RespondsToOwnEvents):
    """
    An object that has events and responds to them, but maintains a registration
    of other objects/callbacks that wish to receive the event as well.
    """
    _event_subscriptions = {}

    def _create_subscription(self, event_type, func):
        return func

    def subscribe_to_event(self, event_type, func):
        """
        Register a callback function to receive an event of a specific type.

        :param event_type: The event type(s) to register the callback to.
        :type event_type: type or tuple

        :param func: The function to call for the given event type(s).
        :type func: types.FunctionType or types.MethodType
        """
        if 'event_delegates' not in self.__dict__:
            self._event_subscriptions = {}
        event_types = (event_type if isinstance(event_type, (tuple, list))
                       else (event_type,))
        for et in event_types:
            if et not in self._event_subscriptions:
                self._event_subscriptions[et] = set()
            self._event_subscriptions[et].add(
                self._create_subscription(et, func))

    def unsubscribe_from_event(self, event_type, func):
        """
        Remove a callback function.

        :param event_type: The event type(s) to unsubscribe from.
        :param func: The function to unsubscribe.
        """
        event_types = (event_type if isinstance(event_type, (tuple, list))
                       else (event_type,))
        for et in event_types:
            sub = self._create_subscription(et, func)
            try:
                self._event_subscriptions[et].remove(sub)
            except KeyError:
                continue

    def respond_to_event(self, event):
        super(HasSubscribableEvents, self).respond_to_event(event)
        self.send_event_to_subscribers(event)

    def send_event_to_subscribers(self, event):
        for event_type, subscribers in self._event_subscriptions.iteritems():
            if isinstance(event, event_type):
                for subscriber in subscribers:
                    subscriber(event)
