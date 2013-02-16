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
        'width': 'auto',
        'lpad': ' ',
        'rpad': ' ',
        'header_formatter': lambda c: c.format_cell(c.name)
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
        settings = self.default_settings
        for key, val in kwargs.iteritems():
            if key in settings:
                settings[key] = val
        self.settings = settings
        self.rows = []
        self.columns = []
        if columns is not None:
            for col in columns:
                self.addColumn(col)

    def addColumn(self, col, width=None, align=None):
        if not isinstance(col, TableColumn):
            col = TableColumn(col, width=width, align=align)
        else:
            if width is not None:
                col.width = width
            if align is not None:
                col.align = align
        self.columns.append(col)

    def addRow(self, row):
        """
        @param row: Object containing data for the row. If a list, uses numeric
            offsets. If dict, uses keys mapped to column data_key values. If
            another type, maps column data_keys to keys in object's __dict__.
        @type row: list or dict or object
        """
        self.rows.append(row)

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
            content_area -= ansi.length(s['lpad']) + ansi.length(s['rpad'])
            if s['frame']:
                content_area -= 2

        for index, col in enumerate(cols):
            w = col.width
            if w is None or w == 'auto':
                w = ansi.length(col.name)
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
                    w = int(content_area * m.groups(1) / 100.0)
            if isinstance(w, int):
                widths[index] = w
        if expand is not None:
            if content_area is None:
                raise Exception("Table requires fixed width to use expansion")
            widths[expand] = content_area - sum(widths)

        return widths

    def _build_header(self, settings=None):
        s = settings or self.settings

        # Lists are mutable, so chances are this will already be set when the
        # rows are build, and the next call to _calc_widths() will be fast.
        s['widths'] = self._calc_widths(s)
        widths = s['widths']

        hrule = (s['hrule'] or ' ') + ansi.ANSI_NORMAL
        vrule = (s['vrule'] or ' ') + ansi.ANSI_NORMAL
        junct = (s['junction'] or ' ') + ansi.ANSI_NORMAL
        lp = s['lpad']
        rp = s['rpad'] + ansi.ANSI_NORMAL
        padlen = ansi.length(lp) + ansi.length(rp)

        lines = []
        hr = junct.join([hrule * (w + padlen) for w in widths])
        hf = s['header_formatter']
        heads = vrule.join([lp + c.align_cell(hf(c), widths[i], c.align) + rp
                            for i, c in enumerate(self.columns)])
        if s['frame']:
            hr = junct + hr + junct
            lines.append(hr)
            heads = vrule + heads + vrule
        lines.append(heads)
        lines.append(hr)

        return lines

    def _build_rows(self, settings=None):
        s = settings or self.settings
        rows = self._cells or self._build_cells()
        cols = self.columns
        s['widths'] = self._calc_widths(s)
        w = s['widths']
        vrule = (s['vrule'] or ' ') + ansi.ANSI_NORMAL
        lpad = s['lpad']
        rpad = s['rpad'] + ansi.ANSI_NORMAL
        frame = s['frame']

        lines = []
        for r in rows:
            if isinstance(r, basestring):
                lines.append(r)
                continue
            line = [] if not frame else [vrule]
            line.append(vrule.join([lpad + cols[i].align_cell(v, w[i]) + rpad
                                    for i, v in enumerate(r)]))
            lines.append(''.join(line) + (vrule if frame else ''))

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
                    self._cells.append([cols[i].format_cell(cell)
                                        for i, cell in enumerate(row)])
        return self._cells

    def _row_values(self, row):
        values = [None] * len(self.columns)

        if isinstance(row, basestring):
            values = row
        if isinstance(row, list) or isinstance(row, tuple):
            for i, v in enumerate(row):
                values[i] = v
        else:
            try:
                rowvals = row if isinstance(row, dict) else row.__dict__
            except AttributeError:
                raise Exception("Invalid row object: %s" % repr(row))
            for i, col in enumerate(self.columns):
                key = col.data_key
                if key in rowvals:
                    if callable(rowvals[key]):
                        #noinspection PyCallingNonCallable
                        values[i] = rowvals[key]()
                    else:
                        values[i] = rowvals[key]

        return values

    def _build_table(self, settings=None):
        settings = settings or self.settings

        parts = []
        if settings['show_header']:
            parts.extend(self._build_header(settings))
        parts.extend(self._build_rows(settings))

        if settings['frame']:
            parts.append(parts[0])

        return '\n'.join(parts)

    def __str__(self):
        return self._build_table()


class TableColumn(object):
    align_funcs = {
        'l': ansi.ljust,
        'r': ansi.rjust,
        'c': ansi.center,
    }

    def __init__(self, name, width=None, align=None, data_key=None,
                 cell_formatter=None):
        self.name = name
        self.align = align or 'c'
        self.width = width or 'auto'
        self.data_key = data_key
        self.cell_formatter = cell_formatter or self.default_formatter

    def align_cell(self, cell, width, align=None):
        align = align or self.align
        try:
            func = self.align_funcs[align]
        except KeyError:
            raise Exception("Invalid column alignment: %s" % align)
        return func(ansi.slice(cell, 0, width), width)

    def format_cell(self, val):
        return self.cell_formatter(val)

    def default_formatter(self, val):
        return str(val)
