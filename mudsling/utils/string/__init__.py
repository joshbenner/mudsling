"""
Various string utilities.
"""
import sys

from .ansi import *
from .table import *


def trimDocstring(docstring):
    """
    Trim a docstring and return it in a predictable format.

    @param docstring: The docstring to trim.
    @type docstring: str

    @return: A trimmed docstring
    @rtype: str
    """
    if not docstring:
        return ''
        # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
            # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
            # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
        # Return a single string:
    return '\n'.join(trimmed)


def english_list(things, nothingstr="nothing", andstr=" and ", commastr=", ",
                 finalcommastr=","):
    """
    Returns a string containing an english-style list, separating items with
    a command and using a command with and before the final item.

    @param things: The items to include in the list.
    @param nothingstr: What to return when list is empty.
    @param andstr: The string to use for the 'and'.
    @param commastr: The string to use as the normal separator.
    @param finalcommastr: The string to use as the final separator before and.

    @rtype: str
    """
    things = map(str, things)
    if not things:
        return nothingstr
    if len(things) == 1:
        return things[0]
    if len(things) == 2:
        return andstr.join(things)

    return commastr.join(things[:-1]) + finalcommastr + andstr + things[-1]


def tabletest(who):
    x = Table(
        [
            TableColumn("City name", align='l'),
            "Area", "Population", "Annual Rainfall"
        ],
        #width=80,
        hrule='{b-',
        vrule='{b|',
        junction='{b+',
        lpad=' ',
        rpad=' ',
        header_formatter=lambda c, w, a: '{y' + c.format_cell(c.name, w, a)
    )
    x.addRow(["Adelaide", 1295, 1158259, 600.5])
    x.addRow(["Brisbane", 5905, 1857594, 1146.4])
    x.addRow(["{gDarwin", 112, 120900, 1714.7])
    x.addRow(["Hobart", 1357, 205556, 619.5])
    x.addRow(["Sydney", 2058, 4336374, 1214.8])
    x.addRow(["{rM{ge{bl{mb{yo{Curne", 1566, 3806092, 646.9])
    x.addRow(["Perth", 5386, 1554769, 869.4])

    who.msg(x)
    who.msg(repr(x.__dict__), {'raw': True})
