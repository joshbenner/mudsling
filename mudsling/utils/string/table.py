import re

import prettytable
from prettytable import *

from .ansi import ANSI_PARSER, AnsiWrapper, fill


__all__ = ['Table']

pct_regex = re.compile(r"(\d+)%")


class Table(PrettyTable):
    """
    ANSI-aware table formatter.
    """

    ansi_parser = ANSI_PARSER
    wrapper = AnsiWrapper()

    # True = size to contents, False = use width settings or size to headers
    _auto_widths = True

    # Max width of entire table. Only matters if auto_widths = False and there
    # is a column that expands or there are percentage widths.
    _table_width = 255  # Arbitrary default value.

    # ANSI to prepend to headers.
    _header_ansi = ''

    #: @type: dict
    _set_widths = None

    def __init__(self, fields=None, width=None, auto_width=None,
                 header_ansi=None, **kwargs):
        super(Table, self).__init__(**kwargs)
        self._options.extend(['auto_widths', 'table_width', 'header_ansi'])
        self._set_widths = {}
        if header_ansi is not None:
            self.header_ansi = header_ansi
        if auto_width is not None:
            self.auto_widths = auto_width
        if width is not None:
            self.table_width = width
            self.auto_widths = False

        for field in fields:
            if isinstance(field, Column):
                if field.width is not None:
                    self.auto_widths = False
                self.add_column(field.name, [], align=field.align,
                                valign=field.valign, width=field.width)
            else:
                self.add_column(field, [])

    def add_column(self, name, column, align="c", valign=None, width=None):
        """
        Width is ignored if auto_widths are enabled. Otherwise, it should be an
        integer width or None, in which case the column is sized to the width
        of the field name.
        """
        super(Table, self).add_column(name, column, align, valign)
        self._set_widths[name] = width

    @property
    def auto_widths(self):
        return self._auto_widths

    @auto_widths.setter
    def auto_widths(self, val):
        self._auto_widths = val

    @property
    def table_width(self):
        return self._table_width

    @table_width.setter
    def table_width(self, val):
        self._table_width = val

    @property
    def header_ansi(self):
        return self._header_ansi

    @header_ansi.setter
    def header_ansi(self, val):
        self._header_ansi = val

    def _get_size(self, text):
        return prettytable._get_size(self.ansi_parser.strip_ansi(text))

    def _str_block_width(self, val):
        """
        ANSI-aware version of block width function.
        """
        return prettytable._str_block_width(self.ansi_parser.strip_ansi(val))
        #return prettytable._str_block_width(val)

    def _validate_single_char(self, name, val):
        try:
            assert self._str_block_width(val) == 1
        except AssertionError:
            raise Exception("Invalid value for %s!  "
                            "Must be a string of length 1." % name)

    def _compute_widths(self, rows, options):
        if options["auto_widths"]:
            if options["header"]:
                widths = [self._get_size(field)[0]
                          for field in self._field_names]
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
        else:  # Use explicitly-set widths.
            widths = len(self.field_names) * [0]
            expand = None
            pct_area = options["table_width"]
            if options["border"]:
                pct_area -= 2
            if options["vrules"]:
                pct_area -= len(widths) - 1
            for index, field in enumerate(self._field_names):
                e = self._set_widths[field]
                if isinstance(e, basestring):
                    if e in ('*', 'expand', 'stretch'):
                        expand = index
                        continue
                    m = pct_regex.match(e)
                    if m:
                        widths[index] = int(pct_area * int(m.group(1)) / 100)
                        continue
                    raise Exception("Invalid column width: %s" % repr(e))
                else:
                    widths[index] = (e if e is not None
                                     else self._get_size(field)[0])
            if expand is not None:
                # Calculate width used otherwise
                used = sum(self._get_padding_widths(options)) * len(widths)
                if options["vrules"] in (ALL, FRAME):
                    used += len(widths) - 1
                if options["border"]:
                    used += 2
                used += sum(widths)
                extra = options["table_width"] - used
                widths[expand] = extra
        self._widths = widths

    def _justify(self, text, width, align):
        text += "{n"
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

    def _stringify_header(self, options):
        bits = []
        lpad, rpad = self._get_padding_widths(options)
        if options["border"]:
            if options["hrules"] in (ALL, FRAME):
                bits.append(self._hrule)
                bits.append("\n")
            if options["vrules"] in (ALL, FRAME):
                bits.append(options["vertical_char"])
            else:
                bits.append(" ")
        for field, width, in zip(self._field_names, self._widths):
            if options["fields"] and field not in options["fields"]:
                continue
            if self._header_style == "cap":
                fieldname = field.capitalize()
            elif self._header_style == "title":
                fieldname = field.title()
            elif self._header_style == "upper":
                fieldname = field.upper()
            elif self._header_style == "lower":
                fieldname = field.lower()
            else:
                fieldname = field
            bits.append(" " * lpad + options["header_ansi"]
                        + self._justify(fieldname, width, self._align[field])
                        + "{n " * rpad)
            if options["border"]:
                if options["vrules"] == ALL:
                    bits.append(options["vertical_char"])
                else:
                    bits.append(" ")
                    # If vrules is FRAME, then we just appended a space at end
            # of the last field, when we really want a vertical character
        if options["border"] and options["vrules"] == FRAME:
            bits.pop()
            bits.append(options["vertical_char"])
        if options["border"] and options["hrules"] != NONE:
            bits.append("\n")
            bits.append(self._hrule)
        return "".join(bits)

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
                if options["vrules"] in (ALL, FRAME):
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
                    if options["vrules"] == ALL:
                        bits[y].append(self.vertical_char)
                    else:
                        bits[y].append(" ")
                y += 1

        # If vrules is FRAME, then we just appended a space at the end
        # of the last field, when we really want a vertical character
        for y in range(0, row_height):
            if options["border"] and options["vrules"] == FRAME:
                bits[y].pop()
                bits[y].append(options["vertical_char"])

        if options["border"] and options["hrules"] == ALL:
            bits[row_height - 1].append("\n")
            bits[row_height - 1].append(self._hrule)

        for y in range(0, row_height):
            bits[y] = "".join(bits[y])

        return "\n".join(bits)


class Column(object):
    def __init__(self, name, align='c', valign=None, width=None):
        self.name = name
        self.align = align
        self.valign = valign
        self.width = width
