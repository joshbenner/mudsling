import time
import re


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

    def is_active(self):
        """
        Return True if the ban is currently active.
        """
        if self.expires is None:
            return True
        return time.time() <= self.expires

    def applies_to(self, session):
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

    def applies_to(self, session):
        try:
            return session.player.ref() == self.player.ref()
        except AttributeError:
            return False


class IPBan(Ban):
    """
    A ban that applies to an IP range.
    """
    ip_pattern = ''
    ip_regex = None

    def __init__(self, ip_pattern, *args, **kwargs):
        super(IPBan, self).__init__(*args, **kwargs)
        self.ip_pattern = ip_pattern
        regex = ip_pattern.strip()
        regex = regex.replace('.', '\.')
        regex = regex.replace('*', '\d{1,3}')
        self.ip_regex = re.compile("^%s$" % regex)

    def applies_to(self, session):
        try:
            return True if self.ip_regex.match(session.ip) else False
        except AttributeError:
            return False


def check_bans(session, bans):
    """
    Check an iterable of bans for any that actively apply to the session.

    @return: A list of applicable bans.
    @rtype: C{list}
    """
    return [b for b in bans if b.applies_to(session) and b.is_active()]


def get_bans(db):
    return list(db.get_setting('bans', default=[]))


def add_ban(db, ban):
    bans = get_bans(db)
    bans.append(ban)
    db.set_setting('bans', bans)


def del_ban(db, ban):
    bans = get_bans(db)
    bans.remove(ban)
    db.set_setting('bans', bans)


def find_bans(bans, type=Ban, **filters):
    """
    Find bans of a specific type with matching attribute values.
    @param bans: The bans to search.
    @param type: A class that matching bans must descend from.
    @param filters: Key/val pairs of attribute/value.
    """
    def __match_filters(ban):
        for attr, val in filters.iteritems():
            if getattr(ban, attr, None) != val:
                return False
        return True
    return [b for b in bans if isinstance(b, type) and __match_filters(b)]
