

class ConfigInvalid(Exception):
    pass


class Error(Exception):
    def __init__(self, msg=""):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class PlayerNotConnected(Error):
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

    input = None

    def __init__(self, cmdline=None, msg=None):
        """
        cmdline could be raw string input or a ParsedInput structure.
        """
        self.input = cmdline
        self.message = msg or "Command Invalid."


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
