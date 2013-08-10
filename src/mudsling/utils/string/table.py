import re

from . import ansi


__all__ = ['Table', 'TableColumn']

pct_regex = re.compile(r"(\d+)%")


class Table(object):
    """
    Base table class for simple tabular presentation of data. ANSI-aware.
    """

    #: @type: dict
    settings = {}
    default_settings = {
        'show_header': True,
        'hrule': '-',
        'vrule': '|',
        'junction': '+',
        'frame': True,
        'border_ansi': '{b',
        'width': 'auto',
        'lpad': ' ',
        'rpad': ' ',
        'header_formatter': lambda c: str(c.name),
        'header_args': (),
        'header_hr': True,
        'rowrule': False,
    }

    #: @type: list
    columns = []

    #: @type: list
    rows = []

    #: @type: list
    _cells = None

    def __init__(self, columns=None, **kwargs):
        """
        @type columns: list or None
        """
        settings = dict(self.default_settings)
        for key, val in kwargs.iteritems():
            settings[key] = val
        self.settings = settings
        self.rows = []
        self.columns = []
        if columns is not None:
            for col in columns:
                self.add_column(col)

    def add_column(self, col, width=None, align=None):
        if not isinstance(col, TableColumn):
            col = TableColumn(col, width=width, align=align)
        else:
            if width is not None:
                col.width = width
            if align is not None:
                col.align = align
        self.columns.append(col)

    def add_row(self, row):
        """
        @param row: Object containing data for the row. If a list, uses numeric
            offsets. If dict, uses keys mapped to column data_key values. If
            another type, maps column data_keys to keys in object's __dict__.
        @type row: list or dict or object
        """
        self.rows.append(row)

    def add_rows(self, *rows):
        for row in rows:
            self.add_row(row)

    def _calc_widths(self, settings=None):
        s = settings or self.settings
        if 'widths' in s:
            return s['widths']
        cols = self.columns
        rows = self._cells or self._build_cells()

        widths = len(cols) * [0]

        expand = None
        content_area = None
        if isinstance(s['width'], int):
            content_area = s['width']
            content_area -= len(cols) - 1
            padlen = ansi.length(s['lpad']) + ansi.length(s['rpad'])
            content_area -= padlen * len(cols)
            if s['frame']:
                content_area -= 2

        for index, col in enumerate(cols):
            w = col.width
            if w is None or w == 'auto':
                w = ansi.length(col.name)
                if len(rows):
                    w = max(w, *[ansi.length(row[index])
                                 for row in rows if isinstance(row, list)])
            if isinstance(w, basestring):
                if w in ('*', 'expand', 'fill'):
                    expand = index
                    continue
                m = pct_regex.match(w)
                if m:
                    if content_area is None:
                        raise Exception("Table requires fixed width to use "
                                        "percentage widths")
                    w = int(content_area * int(m.group(1)) / 100.0)
            if isinstance(w, int):
                widths[index] = w
        if expand is not None:
            if content_area is None:
                raise Exception("Table requires fixed width to use expansion")
            widths[expand] = content_area - sum(widths)

        return widths

    def _hr(self, settings=None):
        s = settings or self.settings
        if 'hr' in s:
            return s['hr']
        junct = (s['junction'] or ' ')
        lp = s['lpad']
        rp = s['rpad'] + ansi.ANSI_NORMAL
        padlen = ansi.length(lp) + ansi.length(rp)
        bansi = (s['border_ansi'] or '')
        hrule = (s['hrule'] or ' ')
        hrlen = ansi.length(hrule)
        hr = bansi + junct + junct.join([hrule * ((w + padlen) / hrlen)
                                        for w in s['widths']]) + junct
        s['hr'] = hr
        return hr

    def _build_header(self, settings=None):
        s = settings or self.settings

        # Lists are mutable, so chances are this will already be set when the
        # rows are build, and the next call to _calc_widths() will be fast.
        s['widths'] = self._calc_widths(s)
        widths = s['widths']

        bansi = (s['border_ansi'] or '')
        vrule = bansi + (s['vrule'] or ' ') + ansi.ANSI_NORMAL
        lp = s['lpad']
        rp = s['rpad'] + ansi.ANSI_NORMAL

        lines = []
        hr = self._hr(s)
        hf_func = s['header_formatter']
        hf_args = s['header_args']
        hf = lambda c: hf_func(c, *hf_args)
        heads = vrule.join([lp + c.align_cell(hf(c), widths[i], c.align) + rp
                            for i, c in enumerate(self.columns)])
        if s['frame']:
            lines.append(hr)
            heads = vrule + heads + vrule
        lines.append(heads)
        if s['header_hr']:
            lines.append(hr)

        return lines

    def _build_rows(self, settings=None):
        s = settings or self.settings
        rows = self._cells or self._build_cells()
        cols = self.columns
        s['widths'] = self._calc_widths(s)
        w = s['widths']
        bansi = (s['border_ansi'] or '')
        lpad = s['lpad']
        rpad = s['rpad'] + ansi.ANSI_NORMAL
        frame = s['frame']
        vrule = bansi + (s['vrule'] or ' ') + ansi.ANSI_NORMAL
        rowrule = s['rowrule']
        hr = self._hr(s)

        lines = []
        linecount = 0
        for r in rows:
            linecount += 1
            if isinstance(r, basestring):
                lines.append(r)
                continue
            line = []
            row_cells = []
            max_lines = 1
            for i, val in enumerate(r):
                cell_content = cols[i].align_cell(val, w[i])
                cell_lines = cell_content.split('\n')
                max_lines = max(max_lines, len(cell_lines))
                row_cells.append(cell_lines)
            if max_lines == 1:
                vr = vrule if frame else ''
                line = ''.join([
                    vr,
                    vrule.join(lpad + cols[i].align_cell(c[0], w[i]) + rpad
                               for i, c in enumerate(row_cells)),
                    vr
                ])
            else:
                # Fill in empty cells.
                empty_cells = [cols[i].align_cell('', w[i])
                               for i in range(len(cols))]
                for ii, cell_lines in enumerate(row_cells):
                    if len(cell_lines) < max_lines:
                        filler = max_lines - len(cell_lines)
                        if filler:
                            row_cells[ii] += [empty_cells[ii]] * filler
                # Build rows, accounting for multiple lines.
                for i in range(max_lines):
                    line.append(vrule if frame else '')
                    line.extend(vrule.join(lpad + c[i] + rpad
                                           for c in row_cells))
                    line.append(vrule if frame else '')
                    if i < (max_lines - 1):
                        line.append('\n')
            lines.append(''.join(line))
            if rowrule and linecount < len(rows):
                lines.append(hr)

        return lines

    def _build_cells(self, rebuild=False):
        if self._cells is None or rebuild:
            self._cells = []
            rows = [self._row_values(row) for row in self.rows]
            cols = self.columns
            for i, row in enumerate(rows):
                if isinstance(row, basestring):
                    self._cells.append(row)
                else:
                    self._cells.append([cols[ii].format_cell(cell)
                                        for ii, cell in enumerate(row)])
        return self._cells

    def _row_values(self, row):
        values = [None] * len(self.columns)

        if isinstance(row, basestring):
            values = row
        if isinstance(row, list) or isinstance(row, tuple):
            for i, v in enumerate(row):
                values[i] = v
        elif isinstance(row, dict):
            for i, col in enumerate(self.columns):
                key = col.data_key
                if key in row:
                    if callable(row[key]):
                        #noinspection PyCallingNonCallable
                        values[i] = row[key]()
                    else:
                        values[i] = row[key]
        else:
            for i, col in enumerate(self.columns):
                if col.data_key is None:
                    values[i] = row
                else:
                    try:
                        attr = getattr(row, col.data_key, None)
                        if callable(attr):
                            values[i] = attr()
                        else:
                            values[i] = attr
                    except AttributeError:
                        values[i] = ''

        return values

    def _build_table(self, settings=None):
        settings = settings or self.settings

        parts = []
        if settings['show_header']:
            parts.extend(self._build_header(settings))
        parts.extend(self._build_rows(settings))

        if settings['frame'] and settings['show_header']:
            parts.append(parts[0])

        return parts

    def __str__(self):
        return '\n'.join(self._build_table())


class TableColumn(object):
    align_funcs = {
        'l': ansi.ljust,
        'r': ansi.rjust,
        'c': ansi.center,
    }

    def __init__(self, name, width=None, align=None, data_key=None,
                 cell_formatter=None, formatter_args=(), wrap=False):
        self.name = name
        self.align = align or 'c'
        self.width = width or 'auto'
        self.data_key = data_key
        self.cell_formatter = cell_formatter or self.default_formatter
        self.formatter_args = formatter_args
        self.wrap = wrap

    def align_cell(self, cell, width, align=None):
        align = align or self.align
        try:
            func = self.align_funcs[align]
        except KeyError:
            raise Exception("Invalid column alignment: %s" % align)
        lns = cell.split('\n')
        if not self.wrap or (len(lns) < 2 and ansi.length(lns[0]) <= width):
            wrapped = lns
        else:
            wrapped = []
            for line in lns:
                wrapped.extend(ansi.wrap(line, width) or [''])
        return '\n'.join(func(ansi.slice(line, 0, width), width)
                         for line in wrapped)

    def format_cell(self, val, args=None):
        args = args or self.formatter_args
        return self.cell_formatter(val, *args)

    def default_formatter(self, val):
        return str(val)
