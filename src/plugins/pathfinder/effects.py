import time

from mudsling import errors

import pathfinder
from .events import EventResponder
from .modifiers import Types as mod_types
from .errors import DataNotFound
from pathfinder import parse_feat

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
                 'payload')

    def __init__(self, modifier, source=None, subject=None):
        """
        @type modifier: L{pathfinder.modifiers.Modifier}
        """
        self.modifier = modifier
        self.source = source
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

    def apply_to(self, subject):
        """
        @type subject: L{pathfinder.objects.PathfinderObject}
        """
        # Lots of payload resolution is performed here, because all the data
        # may not yet be registered to make matching work when effects are
        # initialized, but the data should be reigstered by the time effects
        # are applied.
        from .characters import is_pfchar
        from .objects import is_pfobj
        self.start_time = time.time()
        if self.type == mod_types.language:
            self.payload = pathfinder.data.match(self.modifier.payload,
                                                 types=('language',))
        elif self.type == mod_types.grant:
            try:
                self.payload = parse_feat(self.modifier.payload)
            except errors.MatchError:
                # Just do nothing in this case. They get no feat!
                pathfinder.logger.warning("Unknown feat: %s"
                                          % str(self.modifier.payload))
            else:
                if is_pfchar(subject):
                    subject.add_feat(*self.payload, source=self)
        elif self.type == mod_types.condition:
            self.payload = self.modifier.payload
            try:
                if is_pfobj(subject):
                    subject.add_condition(self.payload, source=self)
            except DataNotFound:
                # Ignore the effect.
                pathfinder.logger.warning("Unknown condition: %s"
                                          % self.payload)
        elif self.type in (mod_types.damage_reduction,
                           mod_types.damage_resistance):
            self.payload = self.modifier.payload
        elif self.type == mod_types.bonus:
            # Resolve stat name at application time just in case.
            self.payload = subject.resolve_stat_name(self.modifier.payload[1])
        if self.modifier.expiration is not None:
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
        subject._apply_effect(self)

    def remove_from(self, subject):
        from .characters import is_pfchar
        from .objects import is_pfobj
        if self.type == mod_types.grant and is_pfchar(subject):
            feat = subject.get_feat(*self.payload)
            subject.remove_feat(feat, source=self)
        elif self.type == mod_types.condition and is_pfobj(subject):
            for condition in subject.get_conditions(self.payload, source=self):
                subject.remove_condition(condition)

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
        if event.name == 'stat mods':
            if self.type == mod_types.bonus and self.payload[0] == event.stat:
                if event.tags == () or event.tags == self.payload[1]:
                    event.modifiers[self] = self.modifier.payload[0]
        elif event.name == 'spoken languages':
            if self.type == mod_types.language and self.payload is not None:
                event.languages.append(self.payload)
        elif event.name == 'damage reduction':
            if self.type == mod_types.damage_reduction:
                value, vulnerable_to = self.payload
                if event.damage_type != vulnerable_to:
                    responses[self] = value
        elif event.name == 'damage resistance':
            if self.type == mod_types.damage_resistance:
                value, resist_type = self.payload
                if event.damage_type == resist_type:
                    return value
