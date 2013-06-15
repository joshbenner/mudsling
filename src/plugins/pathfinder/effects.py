
import time

from .events import EventResponder

time_units = {
    'second': 1,
    'minute': 60,
    'hour': 3600,
    'day': 86400
}


class Effect(EventResponder):
    """
    An Effect is a modifier applied against a specific object at a specific
    point in time.
    """
    __slots__ = ('modifier', 'source', 'start_time', 'expire_type', 'expire',
                 'resolved_stat')

    def __init__(self, modifier, source=None, subject=None):
        self.modifier = modifier
        self.source = source
        if subject is not None:
            self.apply_to(subject)
        else:
            self.start_time = None

    def apply_to(self, subject):
        """
        @type subject: L{pathfinder.objects.PathfinderObject}
        """
        self.start_time = time.time()
        if hasattr(self.modifier, 'stat'):
            self.resolved_stat = subject.resolve_stat_name(self.modifier.stat)
        if self.modifier.duration_roll is not None:
            val = subject.roll(self.modifier.duration_roll)
            if self.modifier.duration_unit in time_units:
                self.expire_type = 'time'
                self.expire = val * time_units[self.modifier.duration_unit]
            else:
                self.expire_type = 'turns'
                self.expire = val
        else:
            self.expire = None
        subject._apply_effect(self)

    def still_applies(self):
        """
        Determine if the effect still applies.
        """
        if self.expire is not None and self.expire_type == 'time':
            return time.time() < self.start_time + self.expire
        # Non-expiring and turn-based expirations are always true until an
        # event removes them. For turn-based expiration, the event is passing
        # the subject's initiative position sufficient times.
        return True

    def respond_to_event(self, event, responses):
        pass
