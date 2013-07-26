from collections import namedtuple
import datetime
import time
import inspect
import functools

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
    def rl_duration(cls, duration):
        return cls.duration(duration)

    @classmethod
    def ic_duration(cls, duration):
        """
        Generate a Duration object based on IC input.

        @param duration: A parseable IC duration string or numeric IC seconds.
        """
        if isinstance(duration, basestring):
            return cls.parse_ic_duration(duration)
        return cls.duration(duration * cls.time_scale)

    @classmethod
    def interval(cls, interval):
        return cls.duration(interval)

    @classmethod
    def date_number(cls, date):
        """
        Given a date input, calculate a number that can be compared to other
        date numbers to determine if the date is the same, comes before, etc.

        Default (Gregorian) generates a numeric date from YYYYMMDD.
        """
        if not isinstance(date, Date):
            date = Date(date, cls)
        ic_unixtime = cls._ic_unixtime(date.timestamp.unix_time)
        ic_date = datetime.datetime.utcfromtimestamp(ic_unixtime)
        return int(ic_date.strftime('%Y%m%d'))

    @classmethod
    def rl_date_span_from_ic_timestamp(cls, timestamp):
        """
        Given a Timestamp input, calculate the RL unixtimes beginning and
        ending the IC date in which the Timestamp falls.

        This may be used in Date initialization, so do not instantiate Date
        here!
        """
        if not isinstance(timestamp, Timestamp):
            timestamp = Timestamp(timestamp, cls)
        ic_unixtime = cls._ic_unixtime(timestamp.unix_time)
        ic_datetime = datetime.datetime.utcfromtimestamp(ic_unixtime)
        s = ic_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        e = ic_datetime.replace(hour=23, minute=59, second=59, microsecond=0)
        start, end = time.mktime(s.timetuple()), time.mktime(e.timetuple())
        return cls._rl_unixtime(start), cls._rl_unixtime(end)

    @classmethod
    def parse_ic_datetime(cls, input):
        """
        Parse a string representing an IC datetime. Default implementation uses
        the Gregorian calendar, so we simply pass this off to parse_datetime.

        @return: A L{Timestamp} based on this L{Calendar}.
        @rtype: L{Timestamp}
        """
        default_ic_dt = datetime.datetime.combine(
            utils.time.get_datetime(cls._ic_unixtime(), tz='UTC'),
            datetime.time()
        )
        # This parses the input as if it was input during the current IC time.
        dt = dateutil.parser.parse(input, ignoretz=True, default=default_ic_dt)
        dt = utils.time.make_aware(dt, utils.time.get_tz('UTC'))
        ic_unixtime = utils.time.unixtime(dt)
        return Timestamp(cls._rl_unixtime(ic_unixtime), cls)

    @classmethod
    def parse_ic_duration(cls, input):
        """
        Parse a string representation of an IC duration. Default implementaiton
        uses the Gregorian calendar, so we parse via time utils.
        @rtype: L{Duration}
        """
        ic_seconds = utils.time.parse_duration(input)
        rl_seconds = ic_seconds / cls.time_scale
        return cls.duration(rl_seconds)

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
        return utils.time.format_timestamp(ic_unixtime, format, tz='UTC')

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


@functools.total_ordering
class Date(namedtuple('Date', 'timestamp')):
    def __new__(cls, date=None, calendar=None):
        """
        @type date: basestring or int or long or float or L{Timestamp}
                    or datetime.date
        @type calendar: basestring or Calendar subclass
        """
        if date is None:
            date = time.time()
        if isinstance(date, Timestamp) and calendar is None:
            calendar = date.calendar
        else:
            calendar = Calendar(calendar)
        if isinstance(date, basestring):
            timestamp = calendar.parse_ic_datetime(date)
        elif isinstance(date, datetime.date):
            dt = datetime.datetime.combine(date, datetime.time())
            timestamp = Timestamp(dt, calendar)
        elif isinstance(date, (int, long, float)):
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
        """
        @rtype: Calendar
        """
        return self.timestamp.calendar

    @property
    def start_rl_unixtime(self):
        return self.calendar.rl_date_span_from_ic_timestamp(self.timestamp)[0]

    @property
    def end_rl_unixtime(self):
        return self.calendar.rl_date_span_from_ic_timestamp(self.timestamp)[1]

    def __getattr__(self, item):
        # Should raise an attribute error upon failure.
        return self.timestamp.calendar.get_part(item)

    def __str__(self):
        return self.calendar.format_date(self)

    def __add__(self, other):
        if isinstance(other, Duration):
            return Date(self.start_rl_unixtime + other.real_seconds,
                        self.calendar)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Date(self.start_rl_unixtime - other.real_seconds,
                        self.calendar)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Date):
            return self.start_rl_unixtime < other.start_rl_unixtime
        elif isinstance(other, Timestamp):
            return other.unix_time < self.start_rl_unixtime
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Date):
            mycal = self.calendar
            ocal = other.calendar
            if mycal == ocal:
                return ocal.date_number(self) == ocal.date_number(other)
            else:
                mystart, myend = self.start_rl_unixtime, self.end_rl_unixtime
                ostart, oend = other.start_rl_unixtime, other.end_rl_unixtime
                return mystart == ostart and myend == oend
        return NotImplemented


@functools.total_ordering
class Timestamp(namedtuple('Timestamp', 'unix_time calendar_name')):
    def __new__(cls, timestamp=None, calendar=None):
        """
        @type timestamp: str or int or long or float or datetime.datetime
                         or Timestamp
        @type calendar: basestring or Calendar subclass
        """
        if calendar is None:
            if isinstance(timestamp, Timestamp):
                # No calendar specified, and a timestamp given as the ref,
                # so let's just use the reference Timestamp's calendar!
                calendar_name = timestamp.calendar.machine_name
            else:
                calendar_name = default_calendar
        elif issubclass(calendar, Calendar):
            calendar_name = calendar.machine_name
        else:
            # Allow potentially bad calendar names to be forgiving, especially
            # during unpickling.
            calendar_name = str(calendar)
        if isinstance(timestamp, basestring):
            # Ask calendar to parse a string into a timestamp object.
            return Calendar(calendar_name).parse_ic_datetime(timestamp)
        if timestamp is None:
            unix_time = time.time()
        elif isinstance(timestamp, datetime.datetime):
            unix_time = utils.time.unixtime(timestamp)
        elif isinstance(timestamp, Timestamp):
            # Calendar can be different, so while we are copying the real time,
            # the IC time may be totally different.
            unix_time = timestamp.unix_time
        elif isinstance(timestamp, (int, long, float)):
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

    @property
    def date(self):
        return Date(self)

    def __str__(self):
        return self.calendar.format_datetime(self)

    def __lt__(self, other):
        if isinstance(other, Timestamp):
            return self.unix_time < other.unix_time
        elif isinstance(other, Date):
            return self.date < other
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Timestamp):
            return self.unix_time == other.unix_time
        elif isinstance(other, Date):
            return self.date == other
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Duration):
            return Timestamp(self.unix_time + other.real_seconds,
                             self.calendar)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Timestamp(self.unix_time - other.real_seconds,
                             self.calendar)
        return NotImplemented


@functools.total_ordering
class Duration(namedtuple('Duration', 'real_seconds calendar_name')):
    def __new__(cls, real_seconds, calendar=None):
        if isinstance(real_seconds, Duration):
            real_seconds = real_seconds.real_seconds
        elif isinstance(real_seconds, basestring):
            real_seconds = utils.time.parse_duration(real_seconds)
        if inspect.isclass(calendar) and issubclass(calendar, Calendar):
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

    def before(self, timestamp=None):
        """
        Get a timestamp before the given timestamp (default now) by the
        Duration's amount.

        @param timestamp: The timestamp before which to generate the output.
        @type timestamp: str or int or float or datetime.datetime or Timestamp
        @return: Timestamp before the given timestamp.
        @rtype: L{Timestamp}
        """
        timestamp = Timestamp(timestamp, self.calendar_name)
        return Timestamp(timestamp.unix_time - self.real_seconds,
                         self.calendar_name)

    def after(self, timestamp=None):
        """
        Get a timestamp after the given timestamp (default now) by the
        Duration's amount.

        @param timestamp: The timestamp after which to generate the output.
        @type timestamp: str or int or float or datetime.datetime or Timestamp
        @return: Timestamp after the given timestamp.
        @rtype: L{Timestamp}
        """
        timestamp = Timestamp(timestamp, self.calendar_name)
        return Timestamp(timestamp.unix_time + self.real_seconds,
                         self.calendar_name)

    def __hash__(self):
        return self.real_seconds

    def __nonzero__(self):
        return True if self.real_seconds else False

    def __lt__(self, other):
        if isinstance(other, Duration):
            return self.real_seconds < other.real_seconds
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Duration):
            return self.real_seconds == other.real_seconds
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(self.real_seconds + other.real_seconds,
                            self.calendar)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Duration(self.real_seconds - other.real_seconds,
                            self.calendar)

    def __mul__(self, other):
        if isinstance(other, (int, long, float)):
            return Duration(self.real_seconds * other, self.calendar)
        return NotImplemented

    def __div__(self, other):
        if isinstance(other, (int, long, float)):
            return Duration(float(self.real_seconds) / other, self.calendar)
        return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, (int, long, float)):
            return Duration(self.real_seconds // other, self.calendar)
        return NotImplemented

    def __mod__(self, other):
        if isinstance(other, (int, long, float)):
            return Duration(self.real_seconds % other, self.calendar)
        return NotImplemented

    def __divmod__(self, other):
        if isinstance(other, (int, long, float)):
            div, mod = divmod(self.real_seconds, other)
            return Duration(div, self.calendar), Duration(mod, self.calendar)
        return NotImplemented


class RealTime(Calendar):
    machine_name = "realtime"


calendars['realtime'] = RealTime
default_calendar = 'realtime'
