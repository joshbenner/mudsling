"""
Various string utilities.
"""
import sys

from mudsling import ansi


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


def length(string, exclude_ansi=True):
    """
    Return the integer length of the string. Defaults to excluding ANSI codes
    from the length.

    @type string: str
    @type exclude_ansi: bool
    @rtype: int
    """
    if exclude_ansi:
        string = ansi.strip_ansi(string)
    return len(string)


def wrap_line(text, cols=100, prefix='', suffix='', indent=0):
    """
    ANSI-aware line wrapping. Wraps single line of text to maximum width.

    @param text: The text to wrap.
    @type text: str

    @param cols: The column width to wrap to.
    @type cols: int

    @param prefix: Text to prefix all lines.
    @type prefix: str

    @param suffix: Text to suffix all lines.
    @type suffix: str

    @param indent: Size of indent of wrapped lines.
    @type indent: int

    @rtype: str
    """


def word_wrap(text, cols=100, prefix='', suffix='', indent=0):
    """
    ANSI-aware line wrapping. Wraps line(s) of text to maximum width. Each new
    line is treated like a paragraph, so existing line breaks will be
    preserved.

    @param text: The text to wrap.
    @type text: str

    @param cols: The column width to wrap to.
    @type cols: int

    @param prefix: Text to prefix all lines.
    @type prefix: str

    @param suffix: Text to suffix all lines.
    @type suffix: str

    @param indent: Size of indent of wrapped lines.
    @type indent: int

    @rtype: str
    """
    paragraphs = [wrap_line(para, cols, prefix, suffix, indent)
                  for para in text.splitlines()]
    return '\n'.join(paragraphs)
