import operator

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.time
from mudsling.utils.string import ansi


class BaseUI(object):

    table_class = utils.string.Table
    table_settings = {}
    Column = utils.string.TableColumn

    h1_format = "{text}"
    h2_format = "{text}"
    h3_format = "{text}"
    hr_format = '----'
    footer_format = "{text}"
    label_format = "{text}:"

    _op_map = {
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
        '=': operator.eq,
        '==': operator.eq,
        '!=': operator.ne
    }

    def h1(self, text=''):
        return self.h1_format.format(text=text)

    def h2(self, text=''):
        return self.h2_format.format(text=text)

    def h3(self, text=''):
        return self.h3_format.format(text=text)

    def hr(self):
        return self.hr_format

    def footer(self, text=''):
        return self.footer_format.format(text=text)

    def body(self, text):
        """
        @rtype: str
        """
        lines = text if isinstance(text, list) else str(text).splitlines()
        return '\n'.join([self.body_line(l) for l in lines])

    def body_line(self, line):
        """
        Prepare a single line/paragraph of text to appear in the body.
        """
        return line

    def _table_settings(self, **kwargs):
        mro = list(self.__class__.__mro__)
        mro.reverse()
        settings = dict(self.table_class.default_settings)
        if 'table_settings' in self.__dict__:
            settings.update(self.table_settings)
        for cls in mro:
            if issubclass(cls, BaseUI):
                settings.update(cls.table_settings)
        settings.update(self.table_settings)
        settings.update(kwargs)
        return settings

    def get_table_setting(self, setting):
        return self._table_settings()[setting]

    def Table(self, columns=None, **kwargs):
        settings = self._table_settings(**kwargs)
        return self.table_class(columns, **settings)

    def report(self, title, body, footer=''):
        report = [self.h1(title), self.body(body)]
        if footer or isinstance(footer, str):
            report.append(self.footer(footer))
        return '\n'.join(report)

    def _label_formatter(self, text):
        return self.label_format.format(text=text)

    def keyval_table(self, keyvals, **kw):
        """
        Create a table with one column for labels and another for values.

        :param keyvals: Iterable of labels and their values as tuples.
        :type keyvals: list of (str, str)

        :return: Table object.
        :rtype: mudsling.utils.string.Table
        """
        params = {'show_header': False, 'frame': False, 'lpad': ''}
        params.update(kw)
        tbl = self.Table(
            [
                self.Column('Label', width='auto', align='r',
                            cell_formatter=self._label_formatter),
                self.Column('Value', width='*', align='l', wrap=True)
            ],
            **params
        )
        tbl.add_rows(*keyvals)
        return tbl

    def format_timestamp(self, timestamp, format='long'):
        if timestamp is None:
            return ''
        try:
            return utils.time.format_timestamp(timestamp, format)
        except (TypeError, ValueError):
            return "ERR"

    def format_interval(self, seconds, format=None,
                        schema=utils.time.realTime):
        return schema.format_interval(seconds, format)

    def format_dhms(self, seconds):
        return utils.time.format_dhms(seconds)

    def conditional_style(self, value, styles=(), formatter=str, suffix='',
                          alternate=None):
        """
        Conditionally apply an ANSI prefix to the string form of the given
        numeric value.

        style format is iterable of (operator, value, prefix string)
        """
        s = alternate if alternate is not None else formatter(value)
        ops = self._op_map
        for opname, val, prefix in styles:
            op = ops[opname] if opname in ops else getattr(operator, opname)
            if op(value, val):
                return prefix + s + suffix
        return s + suffix


class LimitedWidthUI(BaseUI):
    width = 100
    indent = ''

    # Prefix and suffix are NOT counted in the width attribute. The width must
    # bet set to control width of content to appear BETWEEN prefix and suffix.
    # Be sure to properly pad headings!
    body_prefix = ''
    body_suffix = ''

    #: :type: string.AnsiWrapper
    _wrapper = None

    def __init__(self):
        self._wrapper = utils.string.AnsiWrapper(width=self.body_width,
                                                 subsequent_indent=self.indent)

    @property
    def body_width(self):
        l = ansi.length
        return self.width - l(self.body_prefix) - l(self.body_suffix)

    def body_line(self, line):
        p = self.body_prefix
        s = self.body_suffix
        w = self.body_width
        wrapped = self._wrapper.wrap(line)
        return '\n'.join(p + ansi.ljust(l, w) + s for l in wrapped)


class SimpleUI(LimitedWidthUI):
    width = 100
    fill_char = '-'
    body_prefix = ' '
    table_settings = {
        'width': 98,
        'hrule': '-',
        'vrule': '|',
        'junction': '+',
        'header_formatter': lambda c: '{c' + str(c.name),
    }

    def __init__(self, **kwargs):
        settings = ('width', 'fill_char', 'body_prefix', 'table_settings')
        self.table_settings = {}
        for k, v in kwargs.iteritems():
            if k in settings:
                setattr(self, k, v)
        self.table_settings['width'] = self.width - 2 * len(self.body_prefix)
        super(SimpleUI, self).__init__()

    def h1(self, text=''):
        text = '' if text == '' else "{y%s " % text
        return utils.string.ljust("%s{b" % text, self.width, self.fill_char)

    def h2(self, text=''):
        return "{y%s" % text.upper()

    def h3(self, text=''):
        return self.h2(text)

    def hr(self):
        return '-' * self.width

    def footer(self, text=''):
        text = '' if text == '' else " {y%s" % text
        return '{b' + utils.string.rjust(text, self.width, self.fill_char)

    class SimpleUITable(utils.string.Table):
        def _build_header(self, settings=None):
            s = settings or self.settings
            bansi = (s['border_ansi'] or '')
            hrule = ansi.strip_ansi(s['hrule']) or ' '
            junct = ansi.strip_ansi(s['junction']) or ' '

            lines = super(SimpleUI.SimpleUITable, self)._build_header(s)
            if not s['frame']:
                # We still have a top line w/o frame.
                padlen = ansi.length(s['lpad']) + ansi.length(s['rpad'])
                hr = bansi + junct.join([hrule * (w + padlen)
                                         for w in s['widths']])
                lines.insert(0, hr)
            self._hr_stash = lines[0]
            if len(junct):
                lines[0] = lines[0].replace(junct, ' ')
            if len(hrule):
                lines[0] = lines[0].replace(hrule, '_')

            return lines

        def _build_table(self, settings=None):
            s = settings or self.settings
            lines = super(SimpleUI.SimpleUITable, self)._build_table(s)
            if s['frame']:
                lines[-1] = self._hr_stash
            return lines

    table_class = SimpleUITable


class ClassicUI(LimitedWidthUI):
    width = 100
    _hr = '{c' + ('-=' * 50)  # Half width because two chars.
    h1_format = "{{y{text}"
    h2_format = "{{y{text}"
    label_format = "{{c{text}{{y:"
    body_prefix = ' '
    body_suffix = ' '
    table_settings = {
        'width': 98,  # Indent
        'hrule': '-',
        'vrule': '',
        'junction': ' ',
        'frame': False,
        'border_ansi': '{c',
        'lpad': '',
        'rpad': ' ',
        'header_hr': False,
        'header_formatter': lambda c: '{c' + str(c.name),
    }

    def __init__(self, **kwargs):
        settings = ('width', 'h1_format', 'body_prefix', 'body_suffix',
                    'table_settings')
        self.table_settings = {}
        for k, v in kwargs.iteritems():
            if k in settings:
                setattr(self, k, v)
        w = self.width - len(self.body_prefix) - len(self.body_suffix)
        self.table_settings['width'] = w
        if self.width != 100:
            self._hr = '{c' + ('-=' * (self.width / 2))
        super(ClassicUI, self).__init__()

    def h1(self, text=''):
        if text:
            text = ansi.center(super(ClassicUI, self).h1(text), self.width)
        return '\n'.join([self._hr, text, self._hr])

    def h2(self, text=''):
        return super(ClassicUI, self).h2(text.upper())

    def hr(self):
        return self._hr

    def footer(self, text=''):
        lines = [self._hr]
        if text:
            lines.append(super(ClassicUI, self).footer(text))
            lines.append(self._hr)
        return '\n'.join(lines)
