import mudsling.objects
import mudsling.storage

import ictime


class Organization(mudsling.objects.BaseObject):
    """
    Represents some grouping of persons for a common purpose.
    """
    abbreviation = ''
    sovereign = False
    parent_org = None
    ranks = ()


class Rank(object):
    __slots__ = ('name', 'abbreviation', 'seniority')

    def __init__(self, name, abbreviation, seniority):
        self.name = name
        self.abbreviation = abbreviation
        self.seniority = seniority


class Member(mudsling.storage.StoredObject):
    org_memberships = ()


class Membership(object):
    __slots__ = ('org', 'rank', 'timestamp', 'rank_timestamp')

    def __init__(self, org, rank=None, timestamp=None):
        self.org = org
        self.rank = rank
        if timestamp is None:
            timestamp = ictime.Timestamp()
        self.timestamp = timestamp
        self.rank_timestamp = timestamp
