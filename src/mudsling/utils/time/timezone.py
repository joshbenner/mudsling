"""
Timezone handling.

Some code copyright (c) Django Software Foundation and individual contributors.
"""
import time
import datetime
import logging
from ConfigParser import NoSectionError, NoOptionError

import pytz

from mudsling.config import config

__all__ = ('local_tz', 'get_tz', 'is_aware', 'is_naive', 'make_aware',
           'make_naive', 'nowlocal', 'nowutc')

# Cache for local_tz()
__local_tz = None


def local_tz():
    global __local_tz
    if __local_tz is None:
        try:
            __local_tz = pytz.timezone(config.get('Time', 'timezone'))
        except pytz.UnknownTimeZoneError as e:
            __local_tz = pytz.UTC
            logging.error("Invalid timezone in configuration: %s" % e.message)
        except (NoSectionError, NoOptionError):
            __local_tz = pytz.UTC
            logging.warning("No timezone set in configuration!")
    return __local_tz


def nowutc():
    """
    Returns an aware datetime.datetime.
    @rtype: C{datetime.datetime}
    """
    # timeit shows that datetime.now(tz=utc) is 24% slower
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def nowlocal(tz=None):
    """
    Returns an aware datetime using the specified (or local) timezone.
    @rtype: C{datetime.datetime}
    """
    return nowutc().astimezone(tz or local_tz())


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
