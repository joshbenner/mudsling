"""
Based on code with copyright:
    Copyright (c) Django Software Foundation and individual contributors.

PHP date() style date formatting
See http://www.php.net/date for format strings

Usage:
>>> import datetime
>>> d = datetime.datetime.now()
>>> df = DateFormat(d)
>>> print(df.format('jS F Y H:i'))
7th October 2003 11:39
>>>
"""
import re
import time
import calendar
import datetime

from timezone import is_aware, is_naive, local_tz, nowlocal
from dates import MONTHS, MONTHS_3, MONTHS_ALT, MONTHS_AP, WEEKDAYS
from dates import WEEKDAYS_ABBR

__all__ = ('TimeFormat', 'DateFormat')

formatchars = 'aAbBcdDeEfFgGhHiIjlLmMnNoOPrsStTUuwWyYzZ'
re_formatchars = re.compile(r'(?<!\\)([' + formatchars + '])')
re_alt = re.compile(r'%([' + formatchars + '])')
re_escaped = re.compile(r'\\(.)')


class Formatter(object):
    @classmethod
    def format(cls, data, formatstr):
        pieces = []
        for i, piece in enumerate(re_formatchars.split(str(formatstr))):
            if i % 2:
                pieces.append(str(getattr(cls, piece)(data)))
            elif piece:
                pieces.append(re_escaped.sub(r'\1', piece))
        return ''.join(pieces)

    @classmethod
    def alt_format(cls, data, formatstr):
        """
        Similar to .format(), except each replacement code must be preceeded by
        a percent (%) sign. Useful for when you want to sprinkle normal text
        within the format string. It is also a little faster.
        """
        pieces = []
        for i, piece in enumerate(re_alt.split(str(formatstr))):
            if i % 2:
                pieces.append(str(getattr(cls, piece)(data)))
            elif piece:
                pieces.append(piece)
        return ''.join(pieces)


# noinspection PyPep8Naming
class TimeFormat(Formatter):
    @staticmethod
    def a(t):
        """'am' or 'pm'"""
        if t.hour > 11:
            return 'pm'
        return 'am'

    @staticmethod
    def A(t):
        """'AM' or 'PM'"""
        if t.hour > 11:
            return 'PM'
        return 'AM'

    @staticmethod
    def B(t):
        """Swatch Internet time"""
        return '?'  # Not implemented.

    @classmethod
    def f(cls, t):
        """
        Time, in 12-hour hours and minutes, with minutes left off if they're
        zero.
        Examples: '1', '1:30', '2:05', '2'
        Proprietary extension.
        """
        if t.minute == 0:
            return cls.g(t)
        return '%s:%s' % (cls.g(t), cls.i(t))

    @staticmethod
    def g(t):
        """Hour, 12-hour format without leading zeros; i.e. '1' to '12'"""
        if t.hour == 0:
            return 12
        if t.hour > 12:
            return t.hour - 12
        return t.hour

    @staticmethod
    def G(t):
        """Hour, 24-hour format without leading zeros; i.e. '0' to '23'"""
        return t.hour

    @classmethod
    def h(cls, t):
        """Hour, 12-hour format; i.e. '01' to '12'"""
        return '%02d' % cls.g(t)

    @classmethod
    def H(cls, t):
        """Hour, 24-hour format; i.e. '00' to '23'"""
        return '%02d' % cls.G(t)

    @staticmethod
    def i(t):
        """Minutes; i.e. '00' to '59'"""
        return '%02d' % t.minute

    @classmethod
    def P(cls, t):
        """
        Time, in 12-hour hours, minutes and 'a.m.'/'p.m.', with minutes left
        off if they're zero and the strings 'midnight' and 'noon' if
        appropriate.
        Examples: '1 a.m.', '1:30 p.m.', 'midnight', 'noon', '12:30 p.m.'
        Proprietary extension.
        """
        if t.minute == 0 and t.hour == 0:
            return 'midnight'
        if t.minute == 0 and t.hour == 12:
            return 'noon'
        return '%s %s' % (cls.f(t), cls.a(t))

    @staticmethod
    def s(t):
        """Seconds; i.e. '00' to '59'"""
        return '%02d' % t.second

    @staticmethod
    def u(t):
        """Microseconds; i.e. '000000' to '999999'"""
        return '%06d' % t.microsecond


# noinspection PyPep8Naming
class DateFormat(TimeFormat):
    year_days = [None, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

    @staticmethod
    def timezone(dt):
        timezone = None
        if isinstance(dt, datetime.datetime):
            if is_naive(dt):
                timezone = local_tz()
            else:
                timezone = dt.tzinfo
        return timezone

    @staticmethod
    def b(dt):
        """Month, textual, 3 letters, lowercase; e.g. 'jan'"""
        return MONTHS_3[dt.month]

    @staticmethod
    def c(dt):
        """
        ISO 8601 Format
        Example : '2008-01-02T10:30:00.000123'
        """
        return dt.isoformat()

    @staticmethod
    def d(dt):
        """Day of the month, 2 digits with leading zeros; i.e. '01' to '31'"""
        return '%02d' % dt.day

    @staticmethod
    def D(dt):
        """Day of the week, textual, 3 letters; e.g. 'Fri'"""
        return WEEKDAYS_ABBR[dt.weekday()]

    @staticmethod
    def e(dt):
        """Timezone name if available"""
        try:
            if hasattr(dt, 'tzinfo') and dt.tzinfo:
                # Have to use tzinfo.tzname and not datetime.tzname
                # because datatime.tzname does not expect Unicode
                return dt.tzinfo.tzname(dt) or ""
        except NotImplementedError:
            pass
        return ""

    @staticmethod
    def E(dt):
        """Alternative month names as required by some locales. Proprietary
        extension."""
        return MONTHS_ALT[dt.month]

    @staticmethod
    def F(dt):
        """Month, textual, long; e.g. 'January'"""
        return MONTHS[dt.month]

    @classmethod
    def I(cls, dt):
        """'1' if Daylight Savings Time, '0' otherwise."""
        tz = cls.timezone(dt)
        return '1' if tz and tz.dst(dt) else '0'

    @staticmethod
    def j(dt):
        """Day of the month without leading zeros; i.e. '1' to '31'"""
        return dt.day

    @staticmethod
    def l(dt):
        """Day of the week, textual, long; e.g. 'Friday'"""
        return WEEKDAYS[dt.weekday()]

    @staticmethod
    def L(dt):
        """Boolean for whether it is a leap year; i.e. True or False"""
        return calendar.isleap(dt.year)

    @staticmethod
    def m(dt):
        """Month; i.e. '01' to '12'"""
        return '%02d' % dt.month

    @staticmethod
    def M(dt):
        """Month, textual, 3 letters; e.g. 'Jan'"""
        return MONTHS_3[dt.month].title()

    @staticmethod
    def n(dt):
        """Month without leading zeros; i.e. '1' to '12'"""
        return dt.month

    @staticmethod
    def N(dt):
        """
        Month abbreviation in Associated Press style. Proprietary extension.
        """
        return MONTHS_AP[dt.month]

    @staticmethod
    def o(dt):
        """ISO 8601 year number matching the ISO week number (W)"""
        return dt.isocalendar()[0]

    @classmethod
    def O(cls, dt):
        """Difference to Greenwich time in hours; e.g. '+0200', '-0430'"""
        seconds = cls.Z(dt)
        sign = '-' if seconds < 0 else '+'
        seconds = abs(seconds)
        return "%s%02d%02d" % (sign, seconds // 3600, (seconds // 60) % 60)

    @classmethod
    def r(cls, dt):
        """RFC 2822 formatted date; e.g. 'Thu, 21 Dec 2000 16:01:07 +0200'"""
        return cls.alt_format(dt, '%D, %j %M %Y %H:%i:%s %O')

    @staticmethod
    def S(dt):
        """English ordinal suffix for the day of the month,
        2 characters; i.e. 'st', 'nd', 'rd' or 'th'"""
        if dt.day in (11, 12, 13):  # Special case
            return 'th'
        last = dt.day % 10
        if last == 1:
            return 'st'
        if last == 2:
            return 'nd'
        if last == 3:
            return 'rd'
        return 'th'

    @staticmethod
    def t(dt):
        """Number of days in the given month; i.e. '28' to '31'"""
        return '%02d' % calendar.monthrange(dt.year, dt.month)[1]

    @classmethod
    def T(cls, dt):
        """Time zone of this machine; e.g. 'EST' or 'MDT'"""
        tz = cls.timezone(dt)
        name = tz and tz.tzname(dt) or None
        if name is None:
            name = cls.O(dt)
        return name

    @staticmethod
    def U(dt):
        """Seconds since the Unix epoch (January 1 1970 00:00:00 GMT)"""
        if isinstance(dt, datetime.datetime) and is_aware(dt):
            return int(calendar.timegm(dt.utctimetuple()))
        else:
            return int(time.mktime(dt.timetuple()))

    @staticmethod
    def w(dt):
        """Day of the week, numeric, i.e. '0' (Sunday) to '6' (Saturday)"""
        return (dt.weekday() + 1) % 7

    @classmethod
    def W(cls, dt):
        """ISO-8601 week number of year, weeks starting on Monday"""
        # Algorithm from http://www.personal.ecu.edu/mccartyr/ISOwdALG.txt
        jan1_weekday = dt.replace(month=1, day=1).weekday() + 1
        weekday = dt.weekday() + 1
        day_of_year = cls.z(dt)
        if day_of_year <= (8 - jan1_weekday) and jan1_weekday > 4:
            if jan1_weekday == 5 or (jan1_weekday == 6 and
                                     calendar.isleap(dt.year - 1)):
                week_number = 53
            else:
                week_number = 52
        else:
            if calendar.isleap(dt.year):
                i = 366
            else:
                i = 365
            if (i - day_of_year) < (4 - weekday):
                week_number = 1
            else:
                j = day_of_year + (7 - weekday) + (jan1_weekday - 1)
                week_number = j // 7
                if jan1_weekday > 4:
                    week_number -= 1
        return week_number

    @staticmethod
    def y(dt):
        """Year, 2 digits; e.g. '99'"""
        return str(dt.year)[2:]

    @staticmethod
    def Y(dt):
        """Year, 4 digits; e.g. '1999'"""
        return dt.year

    @classmethod
    def z(cls, dt):
        """Day of the year; i.e. '0' to '365'"""
        doy = cls.year_days[dt.month] + dt.day
        if cls.L(dt) and dt.month > 2:
            doy += 1
        return doy

    @classmethod
    def Z(cls, dt):
        """
        Time zone offset in seconds (i.e. '-43200' to '43200'). The offset for
        timezones west of UTC is always negative, and for those east of UTC is
        always positive.
        """
        tz = cls.timezone(dt)
        if not tz:
            return 0
        offset = tz.utcoffset(dt)
        # `offset` is a datetime.timedelta. For negative values (to the west of
        # UTC) only days can be negative (days=-1) and seconds are always
        # positive. e.g. UTC-1 -> timedelta(days=-1, seconds=82800, 0)
        # Positive offsets have days=0
        return offset.days * 86400 + offset.seconds
