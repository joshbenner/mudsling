from mudsling.parse import ParsedInput


class ConfigInvalid(Exception):
    pass


class Error(Exception):
    def __init__(self, msg=""):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class InvalidTask(Error):
    pass


class InvalidObject(Error):
    def __init__(self, obj=None, msg="Invalid Object"):
        super(InvalidObject, self).__init__(msg)
        self.obj = obj


class MatchError(Error):
    pass


class AmbiguousMatch(MatchError):
    def __init__(self, msg=None, query=None, matches=None):
        if msg is None:
            self.message = "Ambiguous match"
            if query is not None:
                self.message += " for '%s'" % query


class FailedMatch(MatchError):
    def __init__(self, msg=None, query=None):
        if msg is None:
            self.message = "Failed match"
            if query is not None:
                self.message += " for '%s'" % query


class CommandInvalid(Error):

    input = None

    def __init__(self, cmdline=None):
        """
        cmdline could be raw string input or a ParsedInput structure.
        """
        if isinstance(cmdline, ParsedInput):
            self.input = cmdline
        self.message = "Command Invalid."
