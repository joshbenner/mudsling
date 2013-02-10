"""
Various string utilities.

ANSI adapted from Evennia. Original ANSI code LICENSE:

BSD license
===========

Copyright (c) 2012-, Griatch (griatch <AT> gmail <DOT> com), Gregory Taylor
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
- Neither the name of the Copyright Holders nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import sys
import textwrap
import re
import operator

import prettytable


# ANSI definitions
ANSI_BEEP = "\07"
ANSI_ESCAPE = "\033"
ANSI_NORMAL = "\033[0m"

ANSI_UNDERLINE = "\033[4m"
ANSI_HILITE = "\033[1m"
ANSI_BLINK = "\033[5m"
ANSI_INVERSE = "\033[7m"
ANSI_INV_HILITE = "\033[1;7m"
ANSI_INV_BLINK = "\033[7;5m"
ANSI_BLINK_HILITE = "\033[1;5m"
ANSI_INV_BLINK_HILITE = "\033[1;5;7m"

# Foreground colors
ANSI_BLACK = "\033[30m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"
ANSI_WHITE = "\033[37m"

# Background colors
ANSI_BACK_BLACK = "\033[40m"
ANSI_BACK_RED = "\033[41m"
ANSI_BACK_GREEN = "\033[42m"
ANSI_BACK_YELLOW = "\033[43m"
ANSI_BACK_BLUE = "\033[44m"
ANSI_BACK_MAGENTA = "\033[45m"
ANSI_BACK_CYAN = "\033[46m"
ANSI_BACK_WHITE = "\033[47m"

# Formatting Characters
ANSI_RETURN = "\r\n"
ANSI_TAB = "\t"
ANSI_SPACE = " "

# Escapes
ANSI_ESCAPES = ("{{", "%%", "\\\\")


class ANSIParser(object):
    """
    A class that parses ansi markup
    to ANSI command sequences

    We also allow to escape colour codes
    by prepending with a \ for mux-style and xterm256,
    an extra { for Merc-style codes
    """

    def __init__(self):
        # Sets the mappings

        # MUX-style mappings %cr %cn etc
        self.mux_ansi_map = [
            # commented out by default; they are potentially annoying
            (r'%r', ANSI_RETURN),
            (r'%t', ANSI_TAB),
            (r'%b', ANSI_SPACE),
            #(r'%cf', ANSI_BLINK),
            #(r'%ci', ANSI_INVERSE),
            (r'%cr', ANSI_RED),
            (r'%cR', ANSI_BACK_RED),
            (r'%cg', ANSI_GREEN),
            (r'%cG', ANSI_BACK_GREEN),
            (r'%cy', ANSI_YELLOW),
            (r'%cY', ANSI_BACK_YELLOW),
            (r'%cb', ANSI_BLUE),
            (r'%cB', ANSI_BACK_BLUE),
            (r'%cm', ANSI_MAGENTA),
            (r'%cM', ANSI_BACK_MAGENTA),
            (r'%cc', ANSI_CYAN),
            (r'%cC', ANSI_BACK_CYAN),
            (r'%cw', ANSI_WHITE),
            (r'%cW', ANSI_BACK_WHITE),
            (r'%cx', ANSI_BLACK),
            (r'%cX', ANSI_BACK_BLACK),
            (r'%ch', ANSI_HILITE),
            (r'%cn', ANSI_NORMAL),
        ]

        # Expanded mapping {r {n etc
        hilite = ANSI_HILITE
        normal = ANSI_NORMAL
        self.ext_ansi_map = [
            (r'{r', hilite + ANSI_RED),
            (r'{R', normal + ANSI_RED),
            (r'{g', hilite + ANSI_GREEN),
            (r'{G', normal + ANSI_GREEN),
            (r'{y', hilite + ANSI_YELLOW),
            (r'{Y', normal + ANSI_YELLOW),
            (r'{b', hilite + ANSI_BLUE),
            (r'{B', normal + ANSI_BLUE),
            (r'{m', hilite + ANSI_MAGENTA),
            (r'{M', normal + ANSI_MAGENTA),
            (r'{c', hilite + ANSI_CYAN),
            (r'{C', normal + ANSI_CYAN),
            (r'{w', hilite + ANSI_WHITE),  # pure white
            (r'{W', normal + ANSI_WHITE),  # light grey
            (r'{x', hilite + ANSI_BLACK),  # dark grey
            (r'{X', normal + ANSI_BLACK),  # pure black
            (r'{n', normal)                # reset
        ]

        # xterm256 {123, %c134,
        self.xterm256_map = [
            #(r'%c([0-5]{3})', self.parse_rgb),   # %c123 - foreground colour
            #(r'%c(b[0-5]{3})', self.parse_rgb),  # %cb123 - background colour
            (r'{([0-5]{3})', self.parse_rgb),    # {123 - foreground colour
            (r'{(b[0-5]{3})', self.parse_rgb)    # {b123 - background colour
        ]

        # prepare regex matching
        self.ansi_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                         for sub in (self.xterm256_map + self.ext_ansi_map)]
        self.ansi_map = self.ext_ansi_map
        self.xterm256_sub = [(re.compile(sub[0], re.DOTALL), sub[1])
                             for sub in self.xterm256_map]

        # prepare matching ansi codes overall
        self.ansi_regex = re.compile("\033\[[0-9;]+m")

        # escapes - replace doubles with a single instance of each
        self.ansi_escapes = re.compile(r"(%s)" % "|".join(ANSI_ESCAPES),
                                       re.DOTALL)

        tokens = []
        for regex, sub in self.xterm256_map:
            regex = regex.replace('(', '').replace(')', '')
            tokens.append(regex)
        for token, sub in self.ansi_map:
            tokens.append(re.escape(token))
        token_pat = r'(?<!\{)(?:' + '|'.join(tokens) + ')'
        self._token_regex = re.compile(token_pat)
        self.token_regex = re.compile('(%s)' % token_pat)

    def parse_rgb(self, rgbmatch):
        """
        This is a replacer method called by re.sub with the matched
        tag. It must return the correct ansi sequence.

        It checks self.do_xterm256 to determine if conversion
        to standard ansi should be done or not.
        """
        if not rgbmatch:
            return ""
        rgbtag = rgbmatch.groups()[0]

        background = rgbtag[0] == 'b'
        if background:
            red, green, blue = int(rgbtag[1]), int(rgbtag[2]), int(rgbtag[3])
        else:
            red, green, blue = int(rgbtag[0]), int(rgbtag[1]), int(rgbtag[2])

        if self.do_xterm256:
            colval = 16 + (red * 36) + (green * 6) + blue
            #print "RGB colours:", red, green, blue
            return ("\033[%s8;5;%s%s%sm" %
                    (3 + int(background),
                     colval / 100,
                     (colval % 100) / 10,
                     colval % 10))
        else:
            #print "ANSI convert:", red, green, blue
            # xterm256 not supported, convert the rgb value to ansi instead
            if red == green and red == blue and red < 2:
                if background:
                    return ANSI_BACK_BLACK
                elif red >= 1:
                    return ANSI_HILITE + ANSI_BLACK
                else:
                    return ANSI_NORMAL + ANSI_BLACK
            elif red == green and red == blue:
                if background:
                    return ANSI_BACK_WHITE
                elif red >= 4:
                    return ANSI_HILITE + ANSI_WHITE
                else:
                    return ANSI_NORMAL + ANSI_WHITE
            elif red > green and red > blue:
                if background:
                    return ANSI_BACK_RED
                elif red >= 3:
                    return ANSI_HILITE + ANSI_RED
                else:
                    return ANSI_NORMAL + ANSI_RED
            elif red == green and red > blue:
                if background:
                    return ANSI_BACK_YELLOW
                elif red >= 3:
                    return ANSI_HILITE + ANSI_YELLOW
                else:
                    return ANSI_NORMAL + ANSI_YELLOW
            elif red == blue and red > green:
                if background:
                    return ANSI_BACK_MAGENTA
                elif red >= 3:
                    return ANSI_HILITE + ANSI_MAGENTA
                else:
                    return ANSI_NORMAL + ANSI_MAGENTA
            elif green > blue:
                if background:
                    return ANSI_BACK_GREEN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_GREEN
                else:
                    return ANSI_NORMAL + ANSI_GREEN
            elif green == blue:
                if background:
                    return ANSI_BACK_CYAN
                elif green >= 3:
                    return ANSI_HILITE + ANSI_CYAN
                else:
                    return ANSI_NORMAL + ANSI_CYAN
            else:    # mostly blue
                if background:
                    return ANSI_BACK_BLUE
                elif blue >= 3:
                    return ANSI_HILITE + ANSI_BLUE
                else:
                    return ANSI_NORMAL + ANSI_BLUE

    def parse_ansi(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.

        """
        if not string:
            return ''
        self.do_xterm256 = xterm256
        #string = utils.to_str(string)

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.ansi_sub:
                part = sub[0].sub(sub[1], part)
            string += "%s%s" % (part, sep[0].strip())
        if strip_ansi:
            # remove all ansi codes (including those manually inserted)
            string = self.ansi_regex.sub("", string)
        return string

    # Slightly more efficient version.
    def parse_ansi2(self, string, strip_ansi=False, xterm256=False):
        """
        Parses a string, subbing color codes according to
        the stored mapping.

        strip_ansi flag instead removes all ansi markup.
        """
        if not string:
            return ''
        self.do_xterm256 = xterm256
        #string = utils.to_str(string)

        # go through all available mappings and translate them
        parts = self.ansi_escapes.split(string) + [" "]
        string = ""
        for part, sep in zip(parts[::2], parts[1::2]):
            for sub in self.xterm256_sub:
                part = sub[0].sub(sub[1], part)
            for sub in self.ansi_map:
                part = part.replace(sub[0], sub[1])
            string += "%s%s" % (part, sep[0].strip())

        if strip_ansi:
            # remove all ansi codes (including those manually inserted)
            string = self.ansi_regex.sub("", string)

        return string

    def strip_ansi(self, string):
        """
        Strips ANSI tokens and any raw ANSI codes.
        """
        return self.ansi_regex.sub('', self._token_regex.sub('', string))

    def strip_tokens(self, string):
        """
        Strips only ANSI tokens, and will leave raw ANSI codes in place.
        """
        return self._token_regex.sub('', string)

    def escape_tokens(self, string):
        """
        Escape ANSI tokens, but leaves raw ANSI codes alone.
        """
        return self.token_regex.sub(r'{\1', string)

    def length(self, string):
        """
        Returns the integer length of the string without any ANSI tokens or
        raw sequences.
        """
        return len(self.strip_ansi(string))


ANSI_PARSER = ANSIParser()


class AnsiWrapper(textwrap.TextWrapper):
    ansi_parser = ANSI_PARSER

    def _wrap_chunks(self, chunks):
        length = self.ansi_parser.length

        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - length(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = length(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and length(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            # If the last chunk on this line is all whitespace, drop it.
            if (self.drop_whitespace and cur_line
                    and cur_line[-1].strip() == ''):
                del cur_line[-1]

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                lines.append(indent + ''.join(cur_line))

        return lines


class Table(prettytable.PrettyTable):
    """
    ANSI-aware table formatter.
    """

    ansi_parser = ANSI_PARSER
    wrapper = AnsiWrapper()

    def _get_size(self, text):
        return prettytable._get_size(self.ansi_parser.strip_ansi(text))

    def _str_block_width(self, val):
        """
        ANSI-aware version of block width function.
        """
        return prettytable._str_block_width(self.ansi_parser.strip_ansi(val))
        #return prettytable._str_block_width(val)

    def _compute_widths(self, rows, options):
        if options["header"]:
            widths = [self._get_size(field)[0] for field in self._field_names]
        else:
            widths = len(self.field_names) * [0]
        for row in rows:
            for index, value in enumerate(row):
                fieldname = self.field_names[index]
                if fieldname in self.max_width:
                    widths[index] = max(widths[index],
                                        min(self._get_size(value)[0],
                                            self.max_width[fieldname]))
                else:
                    widths[index] = max(widths[index],
                                        self._get_size(value)[0])
        self._widths = widths

    def _justify(self, text, width, align):
        excess = width - self._str_block_width(text)
        if align == "l":
            return text + excess * " "
        elif align == "r":
            return excess * " " + text
        else:
            if excess % 2:
                # Uneven padding
                # Put more space on right if text is of odd length...
                if self._str_block_width(text) % 2:
                    return (excess // 2) * " " + text + (excess // 2 + 1) * " "
                # and more space on left if text is of even length
                else:
                    return (excess // 2 + 1) * " " + text + (excess // 2) * " "
                    # Why distribute extra space this way?  To match the
                    # behaviour of the inbuilt str.center() method.
            else:
                # Equal padding on either side
                return (excess // 2) * " " + text + (excess // 2) * " "

    def _stringify_row(self, row, valign, options):
        for index, field, value, width, in zip(range(0, len(row)),
                                               self._field_names,
                                               row,
                                               self._widths):
            # Enforce max widths
            lines = value.split("\n")
            new_lines = []
            for line in lines:
                if self._str_block_width(line) > width:
                    line = fill(line, width)
                new_lines.append(line)
            lines = new_lines
            value = "\n".join(lines)
            row[index] = value

        row_height = 0
        for c in row:
            h = self._get_size(c)[1]
            if h > row_height:
                row_height = h

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        for y in range(0, row_height):
            bits.append([])
            if options["border"]:
                if options["vrules"] in (prettytable.ALL, prettytable.FRAME):
                    bits[y].append(self.vertical_char)
                else:
                    bits[y].append(" ")

        for field, value, width, in zip(self._field_names, row, self._widths):

            lines = value.split("\n")
            dHeight = row_height - len(lines)
            if dHeight:
                if valign == "m":
                    lines = ([""] * int(dHeight / 2) + lines + [""]
                             * (dHeight - int(dHeight / 2)))
                elif valign == "b":
                    lines = [""] * dHeight + lines
                else:
                    lines = lines + [""] * dHeight

            y = 0
            for l in lines:
                if options["fields"] and field not in options["fields"]:
                    continue

                bits[y].append(" " * lpad
                               + self._justify(l, width, self._align[field])
                               + " " * rpad)
                if options["border"]:
                    if options["vrules"] == prettytable.ALL:
                        bits[y].append(self.vertical_char)
                    else:
                        bits[y].append(" ")
                y += 1

        # If vrules is FRAME, then we just appended a space at the end
        # of the last field, when we really want a vertical character
        for y in range(0, row_height):
            if options["border"] and options["vrules"] == prettytable.FRAME:
                bits[y].pop()
                bits[y].append(options["vertical_char"])

        if options["border"] and options["hrules"] == prettytable.ALL:
            bits[row_height - 1].append("\n")
            bits[row_height - 1].append(self._hrule)

        for y in range(0, row_height):
            bits[y] = "".join(bits[y])

        return "\n".join(bits)


def _parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False):
    """
    Parses a string, subbing color codes as needed.
    """
    return parser.parse_ansi(string, strip_ansi=strip_ansi, xterm256=xterm256)


def parse_ansi(string, strip_ansi=False, parser=ANSI_PARSER, xterm256=False):
    """
    Parses a string, subbing color codes as needed.
    @rtype: str
    """
    return parser.parse_ansi2(string, strip_ansi=strip_ansi, xterm256=xterm256)


def strip_ansi(string, parser=ANSI_PARSER):
    """
    Removes ANSI tokens and raw ANSI codes.
    @rtype: str
    """
    return parser.strip_ansi(string)


def escape_ansi_tokens(string, parser=ANSI_PARSER):
    """
    @rtype: str
    """
    return parser.escape_tokens(string)


def strip_ansi_tokens(string, parser=ANSI_PARSER):
    """
    @rtype: str
    """
    return parser.strip_tokens(string)


def length(string, parser=ANSI_PARSER):
    """
    Return the integer length of the string. Excludes ANSI codes.
    """
    return parser.length(string)


def _strPassThru(func, string, parser, *args, **kwargs):
    """
    @rtype: str
    """
    _s = parser.strip(string)
    s = func(string, *args, **kwargs)
    return s.replace(_s, string)


def center(string, width, fillchar=' ', parser=ANSI_PARSER):
    """
    ANSI-aware centering.
    @rtype: str
    """
    return _strPassThru(str.center, string, parser, width, fillchar)


def ljust(string, width, fillchar=None, parser=ANSI_PARSER):
    """
    ANSI-aware ljust.
    @rtype: str
    """
    return _strPassThru(str.ljust, string, parser, width, fillchar)


def rjust(string, width, fillchar=None, parser=ANSI_PARSER):
    """
    ANSI-aware rjust.
    @rtype: str
    """
    return _strPassThru(str.rjust, string, parser, width, fillchar)


def endswith(string, suffix, start=None, end=None, parser=ANSI_PARSER):
    """
    ANSI-aware endswith.
    @rtype: bool
    """
    return parser.strip(string).endswith(suffix, start, end)


def startswith(string, prefix, start=None, end=None, parser=ANSI_PARSER):
    """
    ANSI-aware startswith.
    @rtype: bool
    """
    return parser.strip(string).startswith(prefix, start, end)


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


def wrap(text, width=78, **kwargs):
    """
    ANSI-aware line wrapping for single paragraph in 'text'.

    Implements same API as textwrap.wrap().

    @rtype: list
    """
    wrapper = AnsiWrapper(width=width, **kwargs)
    return wrapper.wrap(text)


def fill(text, width=78, **kwargs):
    """
    ANSI-aware line wrapping for single paragraph in 'text' to single string
    containing line breaks.

    Implements same API as textwrap.fill().

    @rtype: str
    """
    wrapper = AnsiWrapper(width=width, **kwargs)
    return wrapper.fill(text)


def linewrap(text, width=78, linebreaks=True, **kwargs):
    """
    ANSI-aware wrapping. Considers each line in text to be a separate
    paragraph to be wrapped independently of the other lines. This effectively
    preserves existing linebreaks while introducing new ones to keep keep line
    length within the specified width.

    Implements same API as textwrap.wrap().

    @param linebreaks: Whether to return text with linebreaks or a list.
    @return: A list of string lines.
    @rtype: list
    """
    w = AnsiWrapper(width=width, **kwargs)
    paragraphs = [w.wrap(p) for p in text.splitlines()]
    lines = reduce(operator.iadd, paragraphs)
    return lines if not linebreaks else '\n'.join(lines)


def tabletest(who):
    x = Table(["City name", "Area", "Population", "Annual Rainfall"])
    x.align["City name"] = "l"  # Left align city names
    x.padding_width = 1  # One space between col edges and contents (default)
    x.add_row(["Adelaide", 1295, 1158259, 600.5])
    x.add_row(["Brisbane", 5905, 1857594, 1146.4])
    x.add_row(["{gDarwin", 112, 120900, 1714.7])
    x.add_row(["Hobart", 1357, 205556, 619.5])
    x.add_row(["Sydney", 2058, 4336374, 1214.8])
    x.add_row(["{rM{ge{bl{mb{yo{Curne", 1566, 3806092, 646.9])
    x.add_row(["Perth", 5386, 1554769, 869.4])

    who.msg(x)
