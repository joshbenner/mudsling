from collections import namedtuple

__all__ = ('TimeUnit', 'UnknownTimeUnitError', 'TimeSchema')

TimeUnit = namedtuple('TimeUnit',
                      'seconds, singular, plural, abbrev, abbrev_plural')


class UnknownTimeUnitError(Exception):
    pass


class TimeSchema(object):
    """
    Describes a set of time units used together. Time schema units can describe
    durations, not dates. A time schema is not a calendar, even though some of
    its units are naturally similar to those found on a calendar. The point
    here is that, for instance, a standardized "month" in a time schema might
    be different than a specific "month" in a calendar.
    """
    units = []
    all_unit_names = {}
    default_interval_format = ''

    def __init__(self, *units):
        self.units = []
        for u in units:
            self.add_unit(u)

    def add_unit(self, unit):
        self.units.append(unit)
        names = {}
        for attr in TimeUnit._fields:
            val = getattr(unit, attr, None)
            if isinstance(val, basestring):
                names[val] = unit
        self.all_unit_names.update(names)

    def get_unit(self, unit_name):
        unit = self.all_unit_names.get(unit_name, None)
        if unit is None:
            raise UnknownTimeUnitError("Unit %r not found." % unit_name)
        return unit

    def format_interval(self, seconds, format=None):
        format = format or self.default_interval_format
        remain = abs(int(seconds))
        s = format
        for unit in self.units:
            token = "%%%s" % unit.singular
            if token in s:
                try:
                    count, remain = divmod(remain, unit.seconds)
                except ZeroDivisionError:
                    count = 0
                s = s.replace(token, str(count))
        return s

    def unit_to_seconds(self, unit_name, num):
        unit = self.get_unit(unit_name)
        return unit.seconds * num

    def units_to_seconds(self, unit_vals):
        """
        Given a key/val iterable of unit names and amounts, output the number
        of seconds represented by those units together.
        """
        is_dict = isinstance(unit_vals, dict)
        iter = unit_vals.iteritems() if is_dict else unit_vals
        return sum(*[self.unit_to_seconds(*i) for i in iter])

