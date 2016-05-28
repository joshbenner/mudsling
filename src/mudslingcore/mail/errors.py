
import mudsling.errors as errors


class MailError(errors.Error):
    pass


class InvalidMessageSequence(MailError):
    pass


class InvalidMessageSet(MailError):
    pass


class InvalidMessageFilter(MailError):
    pass


class InvalidMessageIndex(MailError):
    pass
