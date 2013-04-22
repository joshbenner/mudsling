from __future__ import absolute_import
import time
import datetime
import calendar
import re
import logging
from collections import namedtuple
from ConfigParser import NoSectionError, NoOptionError

import pytz

from mudsling.config import config


dhms_regex = re.compile(
    r"^(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?$")


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


realTime = TimeSchema(
    TimeUnit(31536000, 'year', 'years', 'yr', 'yrs'),
    TimeUnit(2628000, 'month', 'months', 'mo', 'mos'),
    TimeUnit(604800, 'week', 'weeks', 'wk', 'wks'),
    TimeUnit(86400, 'day', 'days', 'dy', 'dys'),
    TimeUnit(3600, 'hour', 'hours', 'hr', 'hrs'),
    TimeUnit(60, 'minute', 'minutes', 'min', 'mins'),
    TimeUnit(1, 'second', 'seconds', 'sec', 'secs'),
)
realTime.default_interval_format = "%yeary %monthm %dayd"

__default_tz = None
def default_tz():
    global __default_tz
    if __default_tz is None:
        try:
            __default_tz = config.get('Time', 'timezone')
        except (NoSectionError, NoOptionError):
            __default_tz = pytz.UTC
            logging.warning("No timezone set in configuration!")
    return __default_tz


def get_tz(tz):
    """
    Given a timezone name or tzinfo instance, return a tzinfo instance.

    @param tz: Timezone name or tzinfo instance.
    @type tz: C{str} or C{datetime.tzinfo}

    @raise TypeError: When provided tz is not a string or tzinfo instance.

    @rtype: C{datetime.tzinfo}
    """
    if isinstance(tz, basestring):
        return pytz.timezone(tz)
    elif isinstance(tz, datetime.tzinfo):
        return tz
    else:
        raise TypeError("get_tz requires a string or tzinfo instance.")


def get_datetime(timestamp, tz=None):
    """
    Given a datetime or UNIX timestamp, return a tz-aware datetime object.

    @param timestamp: Datetime instance or UNIX timestamp.
    @type timestamp: C{int} or C{long} or C{float} or C{datetime.datetime}

    @param tz: Optional timezone for UNIX timestamp or unaware datetime
        instance. Ignored if aware datetime instance is passed in.
    @type tz: C{str} or C{datetime.tzinfo}

    @rtype: C{datetime.datetime}
    """
    tz = get_tz(tz or default_tz())
    if isinstance(timestamp, datetime.datetime):
        dt = timestamp if timestamp.tzinfo else tz.localize(timestamp)
    else:
        # noinspection PyTypeChecker
        dt = datetime.datetime.fromtimestamp(timestamp, tz=tz)
    return dt


def format_timestamp(timestamp, format=None, in_tz=None, out_tz=None):
    """
    Format a given timestamp into a string representation.

    @param timestamp: An integer UNIX timestamp or a datetime instance.
    @param format: The strftime format to use.
    @param in_tz: An optional timezone name or tzinfo instance indicating what
        timezone the input timestamp (if a UNIX timestamp or an unaware
        datetime). Ignored if timestamp is aware datetime instance.
    @param out_tz: An optional timezone name or tzinfo instance indicating what
        timezone to use when formatting the output.
    @rtype: C{str}
    """
    format = format or '%Y-%m-%d %H:%M:%S %z'
    dt = get_datetime(timestamp, in_tz)
    out_tz = get_tz(out_tz or default_tz())
    if in_tz != out_tz:
        dt = dt.astimezone(out_tz)
    return dt.strftime(format)


def parse_dhms(input):
    """
    Parse a string in dhms format and return a dict of the values.

    dhms format = 1d2h3m4s

    @param input: String in dhms format.
    @type input: str
    @rtype: dict
    """
    m = dhms_regex.search(input)
    if m:
        str_vals = m.groupdict(0)
        return dict(zip(str_vals.keys(), map(int, str_vals.values())))
    else:
        raise ValueError("Invalid dhms string")


def dhms_to_seconds(dhms_str):
    """
    Parse dhms string and return the number of seconds it represents.

    @param dhms_str: String in dhms format.
    @type: str
    @rtype: int
    """
    dhms = parse_dhms(dhms_str)
    return dhms['d'] * 86400 + dhms['h'] * 3600 + dhms['m'] * 60 + dhms['s']


def format_dhms(seconds):
    units = ['day', 'hour', 'minute', 'second']
    remain = seconds
    out = ''
    for unit in realTime.units:
        if unit.singular in units:
            count, remain = divmod(remain, unit.seconds)
            if count:
                out += "%d%s" % (count, unit.singular[0])
    return out if out else '0s'  # 0 or sub-1 seconds.


def format_timestamp(timestamp, format="%Y-%m-%d %H:%M:%S"):
    if not isinstance(timestamp, time.struct_time):
        timestamp = time.localtime(timestamp)
    return time.strftime(format, timestamp)


def format_interval(seconds, format=None, schema=realTime):
    return schema.format_interval(seconds, format)
