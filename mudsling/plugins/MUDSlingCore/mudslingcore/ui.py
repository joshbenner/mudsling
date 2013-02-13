from mudsling.utils import string


class BaseUI(object):

    table_class = string.Table
    table_settings = {}

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
        lines = text if isinstance(text, list) else text.splitlines()
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


class LimitedWidthUI(BaseUI):
    width = 100
    indent = 0

    # Prefix and suffix are NOT counted in the width attribute. The width must
    # bet set to control width of content to appear BETWEEN prefix and suffix.
    body_prefix = ''
    body_suffix = ''

    #: @type: string.AnsiWrapper
    _wrapper = None

    def __init__(self):
        self._wrapper = string.AnsiWrapper(width=self.width,
                                           subsequent_indent=self.indent)

    def body_line(self, line):
        return self.body_prefix + self._wrapper.fill(line) + self.body_suffix


class SimpleUI(LimitedWidthUI):
    fill_char = '-'
    table_settings = {
        'hrule': '{b-',
        'vrule': '{b|',
        'junction': '{b+',
    }

    def h1(self, text=''):
        text = '' if text == '' else "{y%s " % text
        return string.ljust("%s{b" % text, self.width, self.fill_char)

    def h2(self, text=''):
        return "{y%s" % text.upper()

    def h3(self, text=''):
        return self.h2(text)

    def footer(self, text=''):
        text = '' if text == '' else " {y%s" % text
        return '{b' + string.rjust(text, self.width, self.fill_char)
