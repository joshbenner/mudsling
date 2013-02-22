from __future__ import absolute_import
import time
import re
from collections import namedtuple


dhms_regex = re.compile(
    r"^(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?$")


TimeUnit = namedtuple('TimeUnit',
                      'seconds, singular, plural, abbrev, abbrev_plural')


class TimeSchema(object):
    """
    Describes a set of time units used together. Time schema units can describe
    durations, not dates. A time schema is not a calendar, even though some of
    its units are naturally similar to those found on a calendar. The point
    here is that, for instance, a standardized "month" in a time schema might
    be different than a specific "month" in a calendar.
    """
    units = []
    default_interval_format = ''

    def __init__(self, *units):
        self.units = units or []

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
    return out


def format_timestamp(timestamp, format="%Y-%m-%d %H:%M:%S"):
    if not isinstance(timestamp, time.struct_time):
        timestamp = time.localtime(timestamp)
    return time.strftime(format, timestamp)


def format_interval(seconds, format=None, schema=realTime):
    return schema.format_interval(seconds, format)
