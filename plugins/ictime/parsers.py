"""
.. module:: ictime.parsers
    :synopsis: Input parsers for obtaining IC time types.
"""

from mudsling.parsers import StaticParser
from mudsling import errors

import ictime


class ICTimestampStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        try:
            return ictime.parse_user_datetime(input)
        except ValueError:
            raise errors.ParseError("Invalid timestamp.")


class ICDateStaticParser(ICTimestampStaticParser):
    @classmethod
    def parse(cls, input):
        try:
            return super(ICDateStaticParser, cls).parse(input).date
        except errors.ParseError:
            raise errors.ParseError("Invalid date.")


class ICDurationStaticParser(StaticParser):
    @classmethod
    def parse(cls, input):
        try:
            return ictime.parse_user_duration(input)
        except ValueError:
            raise errors.ParseError("Invalid duration.")
