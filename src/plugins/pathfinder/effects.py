import time

import pathfinder.events
import pathfinder.combat
from pathfinder.modifiers import Types as mod_types

time_units = {
    'second': 1,
    'minute': 60,
    'hour': 3600,
    'day': 86400
}


class Effect(pathfinder.events.EventResponder):
    """
    An Effect is a modifier applied against a specific object at a specific
    point in time. Effects basically wrap modifiers in state.
    """
    __slots__ = ('modifier', 'source', 'start_time', 'expire_type', 'expire',
                 'elapsed_turns')

    def __init__(self, modifier, source=None, subject=None):
        """
        :type modifier: pathfinder.modifiers.Modifier
        """
        self.modifier = modifier
        self.source = source or modifier.source
        self.elapsed_turns = 0
        if subject is not None:
            self.apply_to(subject)
        else:
            self.start_time = None

    def __str__(self):
        return str(self.modifier)

    def __repr__(self):
        return "Effect: %s" % str(self.modifier)

    @property
    def type(self):
        return self.modifier.type

    @property
    def payload(self):
        return self.modifier.payload

    @property
    def payload_needs_to_be_applied(self):
        return self.type in (mod_types.grant, mod_types.condition)

    @property
    def expires(self):
        """
        :return: True if the effect has an expiration.
        :rtype: bool
        """
        return self.modifier.expiration is not None

    def apply_to(self, subject):
        """
        :type subject: pathfinder.objects.PathfinderObject
        """
        self.start_time = time.time()
        if self.expires:
            duration_roll, duration_unit = self.modifier.expiration
            val = subject.roll(duration_roll)
            if duration_unit in time_units:
                self.expire_type = 'time'
                self.expire = val * time_units[duration_unit]
            else:
                self.expire_type = 'turns'
                self.expire = val
        else:
            self.expire = None
        if self.payload_needs_to_be_applied:
            self.payload.apply_to(subject)
        subject._apply_effect(self)

    def remove_from(self, subject):
        if self.payload_needs_to_be_applied:
            self.payload.remove_from(subject)

    def still_applies(self):
        """
        Determine if the effect still applies.
        """
        if self.expire is not None:
            if self.expire_type == 'time':
                return time.time() < self.start_time + self.expire
            elif self.expire_type == 'turns':
                return self.elapsed_turns >= self.expire
        return True  # Non-expiring.

    def respond_to_event(self, event, responses):
        if event.type == pathfinder.combat.events.turn_started:
            # Just in case DB had effects created on older code.
            if not hasattr(self, 'elapsed_turns'):
                self.elapsed_turns = 0
            # Effects that last a number of rounds expire just before the same
            # initiative count that they began on.
            self.elapsed_turns += 1
        else:
            self.modifier.respond_to_event(event, responses)
