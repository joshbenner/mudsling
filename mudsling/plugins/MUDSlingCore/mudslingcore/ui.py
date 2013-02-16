
from mudsling import utils
import mudsling.utils.string
import mudsling.utils.time
from mudsling.utils.string import ansi


class BaseUI(object):

    table_class = utils.string.Table
    table_settings = {}
    Column = utils.string.TableColumn

    def h1(self, text=''):
        return text

    def h2(self, text=''):
        return text

    def h3(self, text=''):
        return text

    def footer(self, text=''):
        return text

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
        settings = self.table_class.default_settings
        for cls in mro:
            if issubclass(cls, BaseUI):
                settings.update(cls.table_settings)
        settings.update(self.table_settings)
        settings.update(kwargs)
        return settings

    def Table(self, columns=None, **kwargs):
        settings = self._table_settings(**kwargs)
        return self.table_class(columns, **settings)

    def report(self, title, body, footer=''):
        return '\n'.join([self.h1(title),
                          self.body(body),
                          self.footer(footer)])

    def format_timestamp(self, timestamp, format="%Y-%m-%d %H:%M:%S"):
        if timestamp is None:
            return ''
        try:
            return utils.time.format_timestamp(timestamp, format)
        except (TypeError, ValueError):
            return "ERR"


class LimitedWidthUI(BaseUI):
    width = 100
    indent = 0

    # Prefix and suffix are NOT counted in the width attribute. The width must
    # bet set to control width of content to appear BETWEEN prefix and suffix.
    # Be sure to properly pad headings!
    body_prefix = ''
    body_suffix = ''

    #: @type: string.AnsiWrapper
    _wrapper = None

    def __init__(self):
        self._wrapper = utils.string.AnsiWrapper(width=self.width,
                                                 subsequent_indent=self.indent)

    def body_line(self, line):
        return self.body_prefix + self._wrapper.fill(line) + self.body_suffix


class SimpleUI(LimitedWidthUI):
    fill_char = '-'
    body_prefix = ' '
    body_suffix = ' '
    width = 98  # Space on either side adds up to 100 width.
    table_settings = {
        'width': 98,
        'hrule': '{b-',
        'vrule': '{b|',
        'junction': '{b+',
        'header_formatter': lambda c: '{c' + str(c.name),
    }

    def h1(self, text=''):
        text = '' if text == '' else "{y%s " % text
        width = self.width + 2
        return utils.string.ljust("%s{b" % text, width, self.fill_char)

    def h2(self, text=''):
        return "{y%s" % text.upper()

    def h3(self, text=''):
        return self.h2(text)

    def footer(self, text=''):
        text = '' if text == '' else " {y%s" % text
        return '{b' + utils.string.rjust(text, self.width + 2, self.fill_char)

    class SimpleUITable(utils.string.Table):
        def _build_header(self, settings=None):
            s = settings or self.settings
            hrule = ansi.strip_ansi(s['hrule'] or ' ')
            junct = ansi.strip_ansi(s['junction'] or ' ')

            lines = super(SimpleUI.SimpleUITable, self)._build_header(s)
            if s['frame']:
                self._hr_stash = lines[0]
                if len(junct):
                    lines[0] = lines[0].replace(junct, ' ')
                if len(hrule):
                    lines[0] = lines[0].replace(hrule, '_')
            else:
                # We still have a top line w/o frame.
                padlen = ansi.length(s['lpad']) + ansi.length(s['rpad'])
                hr = junct.join([hrule * (w + padlen) for w in s['widths']])
                lines.insert(0, hr)

            return lines

        def _build_rows(self, settings=None):
            s = settings or self.settings
            vrule = ansi.strip_ansi(s['vrule'] or ' ')

            lines = super(SimpleUI.SimpleUITable, self)._build_rows(s)
            if len(vrule):
                for i in xrange(0, len(lines)):
                    lines[i] = lines[i].replace(vrule, ' ')

            return lines

        def _build_table(self, settings=None):
            s = settings or self.settings
            lines = super(SimpleUI.SimpleUITable, self)._build_table(s)
            if s['frame']:
                lines[-1] = self._hr_stash
            return lines

    table_class = SimpleUITable
