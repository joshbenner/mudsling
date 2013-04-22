"""
Timezone handling.

Some code copyright (c) Django Software Foundation and individual contributors.
"""
import datetime
import logging
from ConfigParser import NoSectionError, NoOptionError

import pytz

from mudsling.config import config

__all__ = ('default_tz', 'get_tz', 'localtime', 'is_aware', 'is_naive',
           'make_aware', 'make_naive', 'nowlocal', 'nowutc')

# Cache for default_tz()
__default_tz = None


def default_tz():
    global __default_tz
    if __default_tz is None:
        try:
            __default_tz = pytz.timezone(config.get('Time', 'timezone'))
        except pytz.UnknownTimeZoneError as e:
            __default_tz = pytz.UTC
            logging.error("Invalid timezone in configuration: %s" % e.message)
        except (NoSectionError, NoOptionError):
            __default_tz = pytz.UTC
            logging.warning("No timezone set in configuration!")
    return __default_tz


def nowutc():
    """
    Returns an aware datetime.datetime.
    """
    # timeit shows that datetime.now(tz=utc) is 24% slower
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def nowlocal():
    return nowutc().astimezone(default_tz())


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


def localtime(value, timezone=None):
    """
    Converts an aware datetime.datetime to local time.

    Local time is defined by the current time zone, unless another time zone
    is specified.
    """
    if timezone is None:
        timezone = default_tz()
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value


def is_aware(value):
    """
    Determines if a given datetime.datetime is aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return (value.tzinfo is not None
            and value.tzinfo.utcoffset(value) is not None)


def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None


def make_aware(value, timezone):
    """
    Makes a naive datetime.datetime in a given time zone aware.
    """
    if hasattr(timezone, 'localize'):
        # available for pytz time zones
        return timezone.localize(value, is_dst=None)
    else:
        # may be wrong around DST changes
        return value.replace(tzinfo=timezone)


def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)
