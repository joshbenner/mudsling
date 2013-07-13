from collections import namedtuple
import datetime
import time

import dateutil
import dateutil.parser

from mudsling import utils
import mudsling.utils.time

calendars = {}
default_calendar = None


class Calendar(object):
    """
    Default calendar class implementation handles a "real" time using the
    modern Gregorian calendar (ie: default Python calendar). Subclasses can
    change some settings to offset and/or compress the calendar.

    For instance, if you had a game with 1:3 time ratio set in WWII era, you
    might
    """
    machine_name = ''
    # Schema used for intervals (duration).
    schema = utils.time.realTime

    # The epoc of a calendar establishes a hard link between a moment in RL
    # time and its corresponding moment in IC time. Both moments are expressed
    # as UNIX timestamps. The default Calendar is real-time, so it makes no
    # distinction between IC and RL (hence, both have 0 as the epoc).
    epoc_rl_time = 0
    epoc_ic_time = 0

    # The time scale is the multiple of real-time at which IC time passes. A
    # time scale of 3:1 would have this value set to 3. Default implementation
    # is real time, so the time scale is 1.
    time_scale = 1

    def __new__(cls, calendar=None):
        """
        Calendar and its subclasses are static, so we prevent instantiation.
        Instead, calling Calendar("name") will yield the subclass registered
        with that name or the default calendar.
        """
        if isinstance(calendar, Calendar):
            return calendar
        return calendars.get(calendar, None) or calendars[default_calendar]

    @classmethod
    def _ic_unixtime(cls, rl_unixtime=None):
        """
        Given an RL UNIX timestamp, return the corresponding IC UNIX timestamp.

        This is part of the default implementation, and may not be needed on
        other subclasses which do not do a mapping between points on the
        Gregorian calendar.
        """
        rl = rl_unixtime or time.time()
        return cls.epoc_ic_time + (rl - cls.epoc_rl_time) * cls.time_scale

    @classmethod
    def _rl_unixtime(cls, ic_unixtime=None):
        """
        Inverse of _ic_unixtime.
        """
        ic = ic_unixtime or cls._ic_unixtime()
        return cls.epoc_rl_time + (ic - cls.epoc_ic_time) / cls.time_scale

    @classmethod
    def timestamp(cls, timestamp=None):
        """
        Obtain an L{ictime.timestamp} instance related to this calendar for a
        given timestamp.

        @param timestamp: The source timestamp to convert. May be a UNIX
            timestamp, L{datetime.datetime} instance, or L{ictime.Timestamp}
            instance.
        @type timestamp: C{int} or L{datetime.datetime} or L{ictime.Timestamp}

        @return: An L{ictime.Timestamp} instance corresponding to the provided
            time built against this calendar.
        @rtype: L{ictime.Timestamp}
        """
        return Timestamp(timestamp, cls)

    @classmethod
    def date(cls, date):
        return Date(date, cls)

    @classmethod
    def duration(cls, duration):
        return Duration(duration, cls)

    @classmethod
    def interval(cls, interval):
        return cls.duration(interval)

    @classmethod
    def parse_ic_datetime(cls, input):
        """
        Parse a string representing an IC datetime. Default implementation uses
        the Gregorian calendar, so we simply pass this off to parse_datetime.

        @return: A L{Timestamp} based on this L{Calendar}.
        @rtype: L{Timestamp}
        """
        default_ic_dt = datetime.datetime.combine(
            utils.time.get_datetime(cls._ic_unixtime()),
            datetime.time()
        )
        # This parses the input as if it was input during the current IC time.
        dt = dateutil.parser.parse(input, ignoretz=True, default=default_ic_dt)
        ic_unixtime = utils.time.unixtime(dt)
        return Timestamp(cls._rl_unixtime(ic_unixtime), cls)

    @classmethod
    def get_part(cls, timestamp, part):
        """
        Default implementation for IC datetime parts is Gregorian calendar.
        Basically, this default implementation just passes through to datetime.
        """
        d = utils.time.get_datetime(cls._ic_unixtime(timestamp.unix_time))
        return getattr(d, part)

    @classmethod
    def format_datetime(cls, timestamp, format='default'):
        """
        Default implementation formats Gregorian datetime.
        """
        ic_unixtime = cls._ic_unixtime(timestamp.unix_time)
        return utils.time.format_timestamp(ic_unixtime, format)

    @classmethod
    def format_interval(cls, interval, format=None):
        """
        Default implementation formats a real-time interval.
        """
        d = Duration(interval, cls)
        return cls.schema.format_interval(d.real_seconds * cls.time_scale,
                                          format)

    @classmethod
    def format_date(cls, date, format='date_default'):
        """
        Default implementation formats a real-time date.
        """
        date = Date(date, cls)
        ic_unixtime = cls._ic_unixtime(date.timestamp.unix_time)
        return utils.time.format_timestamp(ic_unixtime, format)


class Date(namedtuple('Date', 'timestamp')):
    def __new__(cls, date=None, calendar=None):
        """
        @type date: basestring or int or float or L{Timestamp} or datetime.date
        @type calendar: basestring or Calendar subclass
        """
        calendar = Calendar(calendar)
        if isinstance(date, basestring):
            timestamp = calendar.parse_ic_datetime(date)
        elif isinstance(date, datetime.date):
            dt = datetime.datetime.combine(date, datetime.time())
            timestamp = Timestamp(dt, calendar)
        elif isinstance(date, (int, float)):
            timestamp = Timestamp(date, calendar)
        elif isinstance(date, Timestamp):
            timestamp = date
        elif isinstance(date, Date):
            timestamp = Timestamp(date.timestamp, calendar)
        else:
            raise TypeError("First parameter to Date must be number, string,"
                            " ictime.Timestamp, or datetime.date.")
        return super(Date, cls).__new__(cls, timestamp)

    @property
    def calendar(self):
        return self.timestamp.calendar

    def __getattr__(self, item):
        # Should raise an attribute error upon failure.
        return self.timestamp.calendar.get_part(item)

    def __str__(self):
        return self.calendar.format_date(self)


class Timestamp(namedtuple('Timestamp', 'unix_time calendar_name')):
    def __new__(cls, timestamp=None, calendar=None):
        """
        @type timestamp: int or float or datetime.datetime or L{Timestamp}
        @type calendar: basestring or Calendar subclass
        """
        if issubclass(calendar, Calendar):
            calendar_name = calendar.machine_name
        elif calendar is None:
            calendar_name = default_calendar
        else:
            # Allow potentially bad calendar names to be forgiving, especially
            # during unpickling.
            calendar_name = str(calendar)
        if timestamp is None:
            unix_time = time.time()
        elif isinstance(timestamp, datetime.datetime):
            unix_time = utils.time.unixtime(timestamp)
        elif isinstance(timestamp, Timestamp):
            unix_time = timestamp.unix_time
        elif isinstance(timestamp, (int, float)):
            unix_time = timestamp
        else:
            raise TypeError("First parameter to Timestamp must be number,"
                            " datetime, or ictime.Timestamp instance.")
        return super(Timestamp, cls).__new__(cls, unix_time, calendar_name)

    def __getattr__(self, item):
        # Should raise an attribute error upon failure.
        return self.calendar.get_part(self, item)

    @property
    def calendar(self):
        return (calendars.get(self.calendar_name, None)
                or calendars[default_calendar])

    def __str__(self):
        return self.calendar.format_datetime(self)


class Duration(namedtuple('Duration', 'real_seconds calendar_name')):
    def __new__(cls, real_seconds, calendar=None):
        if isinstance(real_seconds, Duration):
            real_seconds = real_seconds.real_seconds
        if issubclass(calendar, Calendar):
            calendar_name = calendar.machine_name
        elif calendar is None:
            calendar_name = default_calendar
        else:
            # Allow potentially bad calendar names to be forgiving, especially
            # during unpickling.
            calendar_name = str(calendar)
        return super(Duration, cls).__new__(cls, real_seconds, calendar_name)

    @property
    def calendar(self):
        return (calendars.get(self.calendar_name, None)
                or calendars[default_calendar])

    def __str__(self):
        return self.calendar.format_interval(self)


class RealTime(Calendar):
    machine_name = "realtime"


calendars['realtime'] = RealTime
default_calendar = 'realtime'
