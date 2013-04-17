import time
import re


def checkBans(session, bans):
    """
    Check an iterable of bans for any that actively apply to the session.

    @return: A list of applicable bans.
    @rtype: C{list}
    """
    return [b for b in bans if b.appliesTo(session) and b.isActive()]


class Ban(object):
    """
    The base class for a ban record.

    @ivar created: The UNIX timestamp of when the ban was created.
    @ivar createdBy: A ref or string indicating who created the ban.
    @ivar reason: A string describing the reason for the ban.
    @ivar expires: The UNIX timestamp of when the ban ends. None = never.
    """
    created = 0
    createdBy = None
    reason = 'No reason given.'
    expires = None

    _settings = ('created', 'createdBy', 'reason', 'expires')

    def __init__(self, *args, **kwargs):
        self.created = time.time()
        for k, v in kwargs.iteritems():
            if k in self._settings:
                setattr(self, k, v)

    def isActive(self):
        """
        Return True if the ban is currently active.
        """
        if self.expires is None:
            return True
        return time.time() <= self.expires

    def appliesTo(self, session):
        """
        Returns True if the ban applies to the provided session.

        Children must override.
        """
        return False


class PlayerBan(Ban):
    """
    A ban that has been applied to a specific player.
    """
    player = None

    def __init__(self, player, *args, **kwargs):
        super(PlayerBan, self).__init__(*args, **kwargs)
        self.player = player

    def appliesTo(self, session):
        try:
            return session.player.ref() == self.player.ref()
        except AttributeError:
            return False


class IPBan(Ban):
    """
    A ban that applies to an IP range.
    """
    ipPattern = ''
    ipRegex = None

    def __init__(self, ipPattern, *args, **kwargs):
        super(IPBan, self).__init__(*args, **kwargs)
        self.ipPattern = ipPattern
        regex = ipPattern.strip()
        regex = regex.replace('.', '\.')
        regex = regex.replace('*', '\d{1,3}')
        self.ipRegex = re.compile("^%s$" % regex)

    def appliesTo(self, session):
        try:
            return True if self.ipRegex.match(session.ip) else False
        except AttributeError:
            return False
