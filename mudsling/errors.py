

class ConfigInvalid(Exception):
    pass


class Error(Exception):
    def __init__(self, msg=""):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class InvalidClassPath(Error):
    pass


class ClassLoadFailed(Error):
    pass


class AccessDenied(Error):
    """
    Generic access denied error.
    """
    pass


class PlayerNotConnected(Error):
    pass


class NoPlayerAttached(Error):
    pass


class InvalidTask(Error):
    pass


class InvalidObject(Error):
    def __init__(self, obj=None, msg="Invalid Object"):
        super(InvalidObject, self).__init__(msg)
        self.obj = obj


class MatchError(Error):
    pass


class AmbiguousMatch(MatchError):
    query = None
    matches = None

    def __init__(self, msg=None, query=None, matches=None):
        self.query = query
        self.matches = matches
        if msg is None:
            msg = "Ambiguous match"
            if query is not None:
                msg += " for '%s'" % query
        super(AmbiguousMatch, self).__init__(msg)


class FailedMatch(MatchError):
    def __init__(self, msg=None, query=None):
        if msg is None:
            msg = "Failed match"
            if query is not None:
                msg += " for '%s'" % query
        super(FailedMatch, self).__init__(msg)


class PlayerNameError(Error):
    pass


class InvalidPlayerName(PlayerNameError):
    pass


class DuplicatePlayerName(PlayerNameError):
    pass


class InvalidEmail(Error):
    pass


class CommandError(Error):
    """
    A generic error occuring during execution of a command. Should be caught
    by code processing input.
    """
    def __init__(self, msg="An error has occurred."):
        super(CommandError, self).__init__(msg=msg)


class CommandInvalid(CommandError):
    """
    Command is not valid or correct in some way, and cannot continue.
    """

    input = None

    def __init__(self, cmdline=None, msg=None):
        """
        cmdline could be raw string input or a ParsedInput structure.
        """
        self.input = cmdline
        self.message = msg or "Command Invalid."


class SilentError(CommandError):
    """A command error which does not generate a message to the user."""
    pass


class ParseError(Error):
    """
    Something couldn't be parsed. Probably user input!
    """
    pass


class ObjSettingError(Error):
    obj = None
    setting = None

    def __init__(self, obj=None, setting=None, message=''):
        self.obj = obj
        self.setting = setting
        super(ObjSettingError, self).__init__(message)


class SettingNotFound(ObjSettingError):
    def __init__(self, obj=None, setting=None):
        if setting is not None:
            msg = "'%s' setting not found" % setting
            if obj is not None:
                msg += " on %s" % obj.nn
        else:
            msg = "Setting not found"

        super(SettingNotFound, self).__init__(obj, setting, msg)


class InvalidSettingValue(ObjSettingError):
    value = None

    def __init__(self, obj, setting, value):
        self.value = value
        msg = "Invalid value for '%s' setting on %s: %r"
        msg = msg % (setting, obj.nn, value)
        super(InvalidSettingValue, self).__init__(obj, setting, msg)


class MoveError(Error):
    def __init__(self, obj, source, dest, msg=''):
        self.obj = obj
        self.source = source
        self.dest = dest
        super(MoveError, self).__init__(msg=msg)


class RecursiveMove(MoveError):
    def __init__(self, obj, source, dest, msg=None):
        msg = msg or "Cannot move object into itself."
        super(RecursiveMove, self).__init__(obj, source, dest, msg=msg)


class MoveDenied(MoveError):
    def __init__(self, obj, source, dest, denied_by, msg='Move denied'):
        self.denied_by = denied_by
        super(MoveDenied, self).__init__(obj, source, dest, msg=msg)
