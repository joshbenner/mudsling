from __future__ import absolute_import
import datetime
import re
import calendar
import logging

import dateutil
import dateutil.parser

import parsedatetime
#: :type: parsedatetime.Calendar
pdt_cal = parsedatetime.Calendar()

# Hide debug log messages from library.
parsedatetime.log.setLevel(logging.WARN)

from .timeschema import TimeSchema, TimeUnit
from .timezone import *
from .dateformat import *


dhms_regex = re.compile(
    r"^(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?$")

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

formats = {
    'default': '%Y-%m-%d %H:%i:%s %O',
    'date_default': '%Y-%m-%d',
}


def get_datetime(timestamp=None, tz=None):
    """
    Given a datetime or UNIX timestamp, return a tz-aware datetime object. If
    no timestamp is given, use current time.

    @param timestamp: Datetime instance or UNIX timestamp.
    @type timestamp: C{int} or C{long} or C{float} or C{datetime.datetime}

    @param tz: Optional timezone for UNIX timestamp or unaware datetime
        instance. Ignored if aware datetime instance is passed in.
    @type tz: C{str} or C{datetime.tzinfo}

    @rtype: C{datetime.datetime}
    """
    tz = get_tz(tz or local_tz())
    if timestamp is None:
        dt = nowlocal(tz)
    elif isinstance(timestamp, datetime.datetime):
        dt = timestamp if timestamp.tzinfo else tz.localize(timestamp)
    else:
        # noinspection PyTypeChecker
        dt = datetime.datetime.fromtimestamp(timestamp, tz=tz)
    return dt


def unixtime(dt=None):
    """
    Given a datetime instance, return the corresponding UNIX timestamp.
    @type dt: C{datetime.datetime}
    """
    dt = dt or get_datetime()
    if is_naive(dt):
        dt = make_aware(dt, local_tz())
    dt = dt.astimezone(get_tz('UTC'))
    return calendar.timegm(dt.timetuple())


def parse_datetime(input):
    try:
        return dateutil.parser.parse(input, tzinfos=parser_tzinfo)
    except TypeError:
        dt, kind = pdt_cal.parseDT(input, tzinfo=local_tz())
        if kind:
            return dt
    raise ValueError('Cannot parse "%s" as a date/time' % input)


def parse_duration(input):
    return realTime.parse_interval(input)


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


def format_timestamp(timestamp=None, format='default', tz=None,
                     formatter=DateFormat.alt_format):
    """
    Format a UNIX timestamp (using the given or default/local timezone) or a
    datetime instance using the provided format string. Format string is the
    PHP date() format characters with leading % sign.

    see mudsling.utils.time.dateformat.DateFormat.alt_format

    :param timestamp: UNIX timestamp or datetime instance to format.
    :param format: The format string to use.
    :param tz: The timezone for the given UNIX timestamp or naive datetime.
    :param formatter: The formatter function to use.

    :rtype: str
    """
    format = formats.get(format, format)
    d = get_datetime(timestamp, tz=tz) if timestamp is not None else nowlocal()
    return formatter(d, format)


def format_interval(seconds, format=None, schema=realTime):
    return schema.format_interval(seconds, format)


def graduated_interval(seconds, schema=realTime):
    parts = []
    for unit in schema.units:
        count = seconds / unit.seconds
        if count >= 1:
            parts.append((count, unit))
            seconds -= count * unit.seconds
        if seconds <= 0:
            break
    return parts
