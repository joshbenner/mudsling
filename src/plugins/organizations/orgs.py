from mudsling import parsers

from mudslingcore.objsettings import ConfigurableObject, ObjSetting
from mudslingcore.objects import InspectableObject

import ictime

import organizations.errors as errors


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
        ObjSetting(name='sovereign', type=bool, attr='sovereign',
                   parser=parsers.BoolStaticParser),
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
        self.members.remove(who.ref())

    @property
    def org_parentage(self):
        """
        List of parent organization structure.
        :rtype: tuple
        """
        if self.parent_org is None:
            return ()
        else:
            return (self.parent_org,) + self.parent_org.org_parentage

    def make_child_org(self, parent):
        if parent == self:
            raise errors.RecursiveParentage('Org cannot be its own parent.')
        elif self in parent.org_parentage:
            raise errors.RecursiveParentage('Org cannot be in parentage of '
                                            'its own parent.')
        if self.game.db.is_valid(self.parent_org, Organization):
            self.parent_org.unregister_child(self)
        self.parent_org = parent.ref()
        parent.register_child(self)

    def make_independent_org(self):
        if self.game.db.is_valid(self.parent_org, Organization):
            self.parent_org.unregister_child(self)
        self.parent_org = None

    def register_child(self, child):
        if 'child_orgs' not in self.__dict__:
            self.child_orgs = []
        self.child_orgs.append(child.ref())

    def unregister_child(self, child):
        self.child_orgs.remove(child.ref())


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
