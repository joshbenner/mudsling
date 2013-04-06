# todo: Refactor out of utils? io.py?
import zope.interface
from mudsling.sessions import IInputProcessor


class LineReader(object):
    """
    Descendant of InputProcessor which captures one or more lines of input from
    a session, passes the resulting list to a callback, then restores normal
    input capture.

    If callback returns boolean False, the input will remain directed to the
    LineReader and the captured line(s) will be erased.
    """
    zope.interface.implements(IInputProcessor)

    def __init__(self, callback, max_lines=None, end_tokens=('.',), args=()):
        """
        @param callback: The callback which will receive the lines of input.
        @type callback: func

        @param max_lines: The maximum number of lines that can be captured.
        @type max_lines: int

        @param end_tokens: A tuple of strings; any of which, appearing on a
            line by themselves, will terminate the capture.
        @type end_tokens: tuple

        @param args: Any additional arguments to pass to the callback.
        @type args: tuple
        """
        if not end_tokens and not max_lines:
            raise ValueError("LineReader must have either a line limit or one"
                             " or more end tokens.")

        self.callback = callback
        self.args = args
        self.max_lines = max_lines
        self.end_tokens = end_tokens

        self.session = None
        self.reset()

    def gainedInputCapture(self, session):
        self.session = session

    def processInput(self, raw):
        if raw in self.end_tokens:
            self.endCapture()
        else:
            self.lines.append(raw)

            if self.max_lines and len(self.lines) >= self.max_lines:
                self.endCapture()

    def endCapture(self):
        """
        Stop capturing input and pass the input to the callback. If callback
        returns boolean False, then capture will be reset and maintained.
        """
        result = self.callback(self.lines, *self.args)
        if result is not False:
            if self.session is not None:
                self.session.resetInputCapture()
        else:
            self.reset()

    def reset(self):
        self.lines = []
