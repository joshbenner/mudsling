from mudslingcore.objsettings import ConfigurableObject, ObjSetting
from mudslingcore.objects import InspectableObject

import ictime


class Organization(ConfigurableObject, InspectableObject):
    """
    Represents some grouping of persons for a common purpose.
    """
    abbreviation = ''
    sovereign = False
    parent_org = None
    child_orgs = []
    ranks = []
    members = []

    object_settings = {
        ObjSetting(name='abbreviation', type=str, attr='abbreviation'),
        ObjSetting(name='sovereign', type=bool, attr='sovereign'),
    }

    @property
    def names(self):
        names = super(Organization, self).names
        if self.abbreviation:
            names += (self.abbreviation,)
        return names

    @property
    def managers(self):
        return tuple(m for m in self.members
                     if m.get_org_membership(self).manager)

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

    def __repr__(self):
        return '%s in %s' % (self.member.name, self.org.name)
