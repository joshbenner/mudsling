import mudsling.objects

import ictime


class Organization(mudsling.objects.BaseObject):
    """
    Represents some grouping of persons for a common purpose.
    """
    abbreviation = ''
    sovereign = False
    parent_org = None
    child_orgs = []
    ranks = []
    members = []

    @property
    def names(self):
        names = super(Organization, self).names
        return names + (self.abbreviation,)

    @property
    def managers(self):
        return tuple(m for m in self.members if m.manages_org(self))

    def is_manager(self, who):
        """
        :type who: organizations.members.Member
        """
        return who in self.managers or who.has_perm('manage orgs')

    def has_member(self, who):
        return who in self.members

    def register_member(self, who):
        if 'members' not in self.__dict__:
            self.members = []
        self.members.append(who.ref())

    def unregister_member(self, who):
        self.members.remove(who)


class Rank(object):
    __slots__ = ('name', 'abbreviation', 'seniority')

    def __init__(self, name, abbreviation, seniority):
        self.name = name
        self.abbreviation = abbreviation
        self.seniority = seniority


class Membership(object):
    __slots__ = ('member', 'org', 'rank', 'timestamp', 'rank_timestamp',
                 'manager')

    def __init__(self, member, org, rank=None, timestamp=None):
        self.member = member.ref()
        self.org = org.ref()
        self.rank = rank
        if timestamp is None:
            timestamp = ictime.Timestamp()
        self.timestamp = timestamp
        self.rank_timestamp = timestamp
        self.manager = False
