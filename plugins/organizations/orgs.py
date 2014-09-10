from collections import OrderedDict

from mudsling import parsers, match

import mudsling.utils.sequence as seq_utils

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
    _autonomous = False
    parent_org = None
    child_orgs = []
    rank_grades = {}
    inherit_rank_grades = True
    inherit_tags = False
    ranks = {}
    _tags = ()

    #: :type: list of organizations.members.Member
    members = []

    object_settings = {
        ObjSetting(name='abbreviation', type=str, attr='abbreviation'),
        ObjSetting(name='sovereign', type=bool, attr='sovereign',
                   parser=parsers.BoolStaticParser),
        ObjSetting(name='autonomous', type=bool, attr='_autonomous',
                   parser=parsers.BoolStaticParser),
        ObjSetting(name='inherit_rank_grades', attr='inherit_rank_grades',
                   type=bool, parser=parsers.BoolStaticParser),
        ObjSetting(name='inherit_tags', type=bool, attr='inherit_tags',
                   parser=parsers.BoolStaticParser),
        ObjSetting(name='tags', type=tuple, attr='_tags',
                   parser=parsers.StringTupleStaticParser)
    }

    @property
    def names(self):
        names = super(Organization, self).names
        if self.abbreviation:
            names += (self.abbreviation,)
        return names

    @property
    def autonomous(self):
        """:rtype: bool"""
        return self.sovereign or self._autonomous

    @property
    def tags(self):
        tags = list(self._tags)
        if self.inherit_tags and self.has_parent:
            tags.extend(self.parent_org.tags)
        return tuple(tags)

    @property
    def managers(self):
        return tuple(m for m in self.members
                     if m.get_org_membership(self).manager)

    @property
    def all_managers(self):
        managers = set(self.managers)
        if not self.autonomous and self.has_parent:
            managers.update(self.parent_org.all_managers)
        return tuple(managers)

    def is_manager(self, who):
        """
        :type who: organizations.members.Member
        """
        return (who in self.managers  # Try this first for efficiency.
                or who.has_perm('manage orgs')
                or who in self.all_managers)

    def add_manager(self, who):
        """
        :param who: The character to flag as a manager.
        :type who: organizations.members.Member
        """
        if not self.has_member(who):
            raise errors.NotInOrg("Managers must first be members.")
        #: :type: Membersip
        membership = who.get_org_membership(self)
        if membership.manager:
            raise errors.AlreadyManager("Member is already a manager.")
        membership.manager = True

    def remove_manager(self, who):
        if not self.has_member(who):
            raise errors.NotInOrg("Member not found.")
        membership = who.get_org_membership(self)
        if not membership.manager:
            raise errors.NotManager("Member is not a manager.")
        membership.manager = False

    def has_member(self, who):
        return who in self.members

    def register_member(self, who):
        if 'members' not in self.__dict__:
            self.members = []
        self.members.append(who.ref())

    def unregister_member(self, who):
        self.members.remove(who.ref())

    @property
    def has_parent(self):
        return self.game.db.is_valid(self.parent_org, Organization)

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

    @property
    def all_rank_grades(self):
        """:rtype: mudsling.utils.sequence.CaselessDict"""
        orgs = [self]
        if self.inherit_rank_grades:
            for org in self.org_parentage:
                orgs.append(org)
                if not org.inherit_rank_grades:
                    break
        orgs.reverse()
        grades = {}
        for org in orgs:
            grades.update(org.rank_grades)
        return seq_utils.CaselessDict(grades)

    def get_rank_grade(self, code, inherited=True):
        """
        :param code: The grade code to retrieve.
        :type code: str
        :param inherited: Whether to include inherited rank grades or not.
        :type inherited: bool
        :return: The rank grade.
        :rtype: RankGrade
        """
        grades = self.all_rank_grades if inherited else self.rank_grades
        if code not in grades:
            raise errors.GradeNotFound('Grade not found.')
        return grades[code]

    def create_rank_grade(self, code, seniority=0, pay=0.0):
        """
        Create a rank grade on this organization.

        :param code: The code name for the rank grade.
        :type code: str
        :param seniority: What level of seniority to give the new rank grade.
        :type seniority: int
        :param pay: The pay scale to apply to the rank grade.
        :type pay: float
        :return: The new rank grade.
        :rtype: RankGrade
        """
        if 'rank_grades' not in self.__dict__:
            self.rank_grades = seq_utils.CaselessDict()
        code = code.upper()
        if code in self.rank_grades:
            raise errors.GradeAlreadyExists('Grade already exists.')
        grade = RankGrade(code, seniority, pay)
        self.rank_grades[code] = grade
        return grade

    def delete_rank_grade(self, code):
        code = code.upper()
        self.get_rank_grade(code, inherited=False)  # Error if not exists.
        for rank in self.ranks:
            if rank.grade_code.upper() == code:
                rank.grade_code = None
        del self.rank_grades[code]

    def match_rank(self, search, exact=False, err=False):
        return match.match_objlist(search, self.ranks.values(), exact=exact,
                                   err=err)

    def create_rank(self, name, abbrev, grade_code=None):
        ranks = self.ranks.values()
        if name.lower() in [r.name.lower() for r in ranks]:
            raise errors.DuplicateRank('Rank name already in use.')
        if abbrev.lower() in [r.abbreviation.lower() for r in ranks]:
            raise errors.DuplicateRank('Rank abbreviation already in use.')
        if grade_code is not None:
            self.get_rank_grade(grade_code)  # Call to get error.
        rank = Rank(self.ref(), name, abbrev, grade_code)
        if 'ranks' not in self.__dict__:
            self.ranks = seq_utils.CaselessDict()
        self.ranks[abbrev] = rank
        return rank

    def delete_rank(self, abbrev):
        if abbrev not in self.ranks:
            raise errors.RankNotFound('Rank not found')
        rank = self.ranks[abbrev]
        for member in self.members:
            membership = member.get_org_membership(self)
            if membership.rank == rank:
                raise errors.RankInUse('Cannot delete ranks that are in use')
        del self.ranks[abbrev]
        return rank

    @property
    def grade_ranks(self):
        """
        Returns an ordered dictionary mapping rank grades to the ranks in each
        grade.
        :rtype: OrderedDict
        """
        sorted_grades = sorted(self.all_rank_grades.values(),
                               key=lambda x: x.seniority)
        grades = OrderedDict((g, []) for g in sorted_grades)
        for rank in self.ranks.itervalues():
            grades[rank.grade].append(rank)
        return grades

    def _next_rank(self, rank, rankset):
        if isinstance(rank, basestring):
            rank = self.match_rank(rank, err=True)[0]
        found_current = False
        for nextranks in rankset:
            if found_current:
                if not nextranks:
                    continue
                if len(nextranks) == 1:
                    return nextranks[0]
                return tuple(nextranks)
            if rank in nextranks:
                found_current = True
        return None

    def next_rank(self, rank):
        """
        Get the rank that comes after the given rank in seniority.

        Returns a tuple of multiple ranks if the next Rank is ambiguous, or
        None if there is no next rank.

        :param rank: The rank whose next senior rank to find.
        :type rank: Rank or str
        :return: The next rank in seniority.
        :rtype: None or Rank or tuple of Rank
        """
        return self._next_rank(rank, self.grade_ranks.values())

    def previous_rank(self, rank):
        """
        Get the rank that comes before the given rank in seniority.

        Returns a tuple of multiple ranks if the previous Rank is ambiguous, or
        None if there is no previous rank.

        :param rank: The rank whose previous senior rank to find.
        :type rank: Rank or str
        :return: The previous rank in seniority.
        :rtype: None or Rank or tuple of Rank
        """
        rankset = self.grade_ranks.values()
        rankset.reverse()
        return self._next_rank(rank, rankset)


class Nation(Organization):
    sovereign = True
    _autonomous = True
    inherit_rank_grades = False
    _tags = ('political',)


class Province(Organization):
    sovereign = False
    _autonomous = True
    inherit_rank_grades = False
    _tags = ('political',)


class Military(Organization):
    sovereign = False
    _autonomous = False
    inherit_rank_grades = False
    _tags = ('military',)


class Company(Organization):
    sovereign = False
    _autonomous = True
    inherit_rank_grades = False
    _tags = ('commercial',)


class Department(Organization):
    sovereign = False
    _autonomous = False
    inherit_rank_grades = True
    inherit_tags = True


class Division(Organization):
    sovereign = False
    _autonomous = False
    inherit_rank_grades = True
    inherit_tags = True


org_types = [
    Organization,
    Nation,
    Province,
    Military,
    Company,
    Department,
    Division,
]


def match_org_type(name, exact=False, err=False, case_sensitive=False):
    stringlists = dict(tuple((t, (t.__name__,)) for t in org_types))
    return match.match_stringlists(name, stringlists, exact=exact, err=err,
                                   case_sensitive=case_sensitive,
                                   ordinal=False)


class RankGrade(object):
    __slots__ = ('code', 'seniority', 'pay')

    def __init__(self, code, seniority=0, pay=0.0):
        self.code = code.upper()
        self.seniority = seniority
        self.pay = pay

    def __repr__(self):
        return '%s: S%d P%0.2f' % (self.code, self.seniority, self.pay)


class Rank(object):
    __slots__ = ('name', 'abbreviation', 'grade_code', 'org')

    def __init__(self, org, name, abbreviation, grade_code=None):
        #: :type: Organization
        self.org = org.ref()
        self.name = name
        self.abbreviation = abbreviation
        self.grade_code = grade_code

    @property
    def names(self):
        return self.name, self.abbreviation

    @property
    def grade(self):
        """:rtype: RankGrade"""
        if self.grade_code is None:
            return None
        return self.org.get_rank_grade(self.grade_code)

    def __repr__(self):
        return '%s (%s)' % (self.name, self.abbreviation)


class Membership(object):
    __slots__ = ('member', 'org', 'rank', 'timestamp', 'rank_timestamp',
                 'manager')

    def __init__(self, member, org, rank=None, timestamp=None):
        #: :type: organizations.members.Member
        self.member = member.ref()
        #: :type: Organization
        self.org = org.ref()
        #: :type: Rank
        self.rank = rank
        if timestamp is None:
            timestamp = ictime.Timestamp()
        self.timestamp = timestamp
        self.rank_timestamp = timestamp
        self.manager = False

    def __repr__(self):
        return '%s in %s' % (self.member.name, self.org.name)

    def set_rank(self, rank):
        if rank != self.org.ranks.get(rank.abbreviation, None):
            raise errors.InvalidRank('Invalid rank for organization.')
        #: :type: Rank
        self.rank = rank
        self.rank_timestamp = ictime.Timestamp()
        self.member.tell('You now hold the rank of {m', rank.name, '{n in {c',
                         self.org, '{n.')
