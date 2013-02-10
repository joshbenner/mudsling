

class BaseUI(object):

    @staticmethod
    def h1(text):
        return text

    @staticmethod
    def h2(text):
        return text

    @staticmethod
    def h3(text):
        return text

    @staticmethod
    def footer(text):
        return text

    @staticmethod
    def body(text):
        return text

    @staticmethod
    def body_lines(lines):
        return '\n'.join(lines)

    @staticmethod
    def table(header=None, rows=None):
        raise NotImplemented


class SimpleUI(BaseUI):

    width = 100

    @staticmethod
    def h1(text):

