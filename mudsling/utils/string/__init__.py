"""
Various string utilities.
"""
import re
import sys
import random
import string
import shlex
import inflect

inflection = inflect.engine()

from .ansi import *
from .table import *

more_random = random.SystemRandom()


def random_string(length, candidates=None):
    candidates = candidates or string.ascii_letters + string.digits
    return ''.join(more_random.choice(candidates) for _ in xrange(length))


def trim_docstring(docstring):
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
                 finalcommastr=",", formatter=str):
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
    things = map(formatter, things)
    if not things:
        return nothingstr
    if len(things) == 1:
        return things[0]
    if len(things) == 2:
        return andstr.join(things)

    return commastr.join(things[:-1]) + finalcommastr + andstr + things[-1]


def columnize(items, numCols, width=79, align='l'):
    items = list(items)
    numRows = (len(items) + numCols - 1) / numCols
    items.extend([''] * (numRows * numCols - len(items)))
    colWidth = 'auto' if width == 'auto' else '%d%%' % (100 / numCols)
    columns = []
    for i in range(0, numCols):
        columns.append(TableColumn('', width=colWidth, align=align))
    table = Table(columns, show_header=False, frame=False, width=width,
                  vrule=' ', lpad='', rpad='')
    for i in range(0, numRows):
        table.add_row(items[i::numRows])
    return str(table)


def tabletest(who):
    x = Table(
        [
            TableColumn("City name", align='l'),
            "Area", "Population", "Rain"
        ],
        #width=80,
        hrule='{b-',
        vrule='{b|',
        junction='{b+',
        lpad=' ',
        rpad=' ',
        header_formatter=lambda c: '{y' + c.format_cell(c.name)
    )
    x.add_row(["Adelaide", 1295, 1158259, 600.5])
    x.add_row(["Brisbane", 5905, 1857594, 1146.4])
    x.add_row(["{gDarwin", 112, 120900, 1714.7])
    x.add_row(["Hobart", 1357, 205556, 619.5])
    x.add_row(["Sydney", 2058, 4336374, 1214.8])
    x.add_row(["{rM{ge{bl{mb{yo{Curne", 1566, 3806092, 646.9])
    x.add_row(["Perth", 5386, 1554769, 869.4])

    who.msg(repr(x._row_values(x.rows[0])))

    who.msg(str(x))


def tablewraptest(who):
    x = Table(
        [
            TableColumn('Item Name', align='l', width=20, wrap=True),
            TableColumn('Description', align='l', width=73, wrap=True)
        ],
        rowrule=True
    )
    x.add_row([
        'Parturient Condimentum',
        '{yCras mattis consectetur purus sit amet fermentum. Nulla vitae elit '
        'libero, a pharetra augue. Duis mollis, est non commodo luctus, nisi '
        'erat porttitor ligula, eget lacinia odio sem nec elit. Cum sociis '
        'natoque penatibus et magnis dis parturient montes, nascetur ridiculus'
        ' mus.'
    ])
    x.add_row([
        'Ornare',
        'Donec ullamcorper nulla non metus auctor fringilla. Etiam porta sem '
        'malesuada magna mollis euismod.'
    ])
    who.tell(x)


def split_quoted_words(text):
    lex = shlex.shlex(text, posix=True)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)


def format_number(value, precision=None):
    """
    Format a number for printing with localized commas and optional precision.

    This is slightly less efficient than doing the .format() call yourself, so
    do not use if performance is critical.

    :param value: The number to format.
    :param precision: How many digits after the decimal to include.
    :return:
    """
    if precision is None:
        if isinstance(value, float):
            precision = len(repr(value).split('.')[1])
        else:
            precision = 0
    fmt = 'd' if precision == 0 else ('.%df' % precision)
    return format(value, ',%s' % fmt)


def singular_noun(noun):
    """
    Convenience function that attempts to singularize a noun. Returns the noun
    that was passed to it if the inflection engine cannot singularize.

    :param noun: The noun to singularize.
    :type noun: str

    :return: A singular noun.
    :rtype: str
    """
    singular = inflection.singular_noun(noun)
    return singular if singular else noun


def plural_noun(noun, count=None):
    """
    Convenience function that attempts to pluralize a noun.

    .. note:: Will re-pluralize any plurals passed to it.

    :param noun: The noun to pluralize.
    :type noun: str

    :param count: An optional parameter to indicate the number associated with
        the noun to conditionally pluralize it.
    :type count: int or float

    :return: The pluralize noun.
    :rtype: str
    """
    return inflection.plural_noun(noun, count)

decamelcase = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


def camelcase_to_spaces(text):
    return decamelcase.sub(r' \1', text)
