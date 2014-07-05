import sys

import mudsling.commands
import mudsling.objects
import mudsling.parsers
import mudsling.locks

import organizations.errors as errors
import organizations.orgs as orgs


class Member(mudsling.objects.BaseCharacter):
    org_memberships = ()

    @property
    def orgs(self):
        return tuple(m.org for m in self.org_memberships)

    @property
    def managed_orgs(self):
        return tuple(m.org for m in self.org_memberships if m.manager)

    def manages_org(self, org):
        return self.has_perm('manage orgs') or org in self.managed_orgs

    def match_org(self, search, exactOnly=False, err=False):
        if self.has_perm('manage orgs'):
            candidates = self.game.db.descendants(orgs.Organization)
        else:
            candidates = self.orgs
        return self._match(search, candidates, exactOnly=exactOnly, err=err)

    def get_org_membership(self, org):
        for membership in self.org_memberships:
            if membership.org == org:
                return membership
        return None

    def in_org(self, org):
        return org in self.orgs

    def join_org(self, org):
        if self.in_org(org):
            raise errors.AlreadyInOrg()
        else:
            membership = orgs.Membership(self, org)
            self.org_memberships += (membership,)
            org.register_member(self)
            self.tell('{gYou are now a member of {c', org, '{g.')

    def leave_org(self, org):
        if not self.in_org(org):
            raise errors.NotInOrg()
        else:
            membership = self.get_org_membership(org)
            self.org_memberships = tuple(m for m in self.org_memberships
                                         if m != membership)
            org.unregister_member(self)
            self.tell('{yYou are no longer a member of {c', org, '{y.')


match_char = mudsling.parsers.MatchDescendants(cls=Member,
                                               search_for='character',
                                               show=True, context=False)


class MatchMyOrgs(mudsling.parsers.Parser):
    def parse(self, input, actor=None):
        return actor.match_org(input, err=True)[0]

match_org = MatchMyOrgs()


class OrgCommand(mudsling.commands.Command):
    """
    Abstract command class for commands regarding organizations.
    """
    abstract = True
    org_manager = False
    lock = mudsling.locks.all_pass

    def prepare(self):
        """
        If there is an 'org' arg, but no org has been specified, then this
        method will attempt to infer which org the command is regarding.

        Prevent the command if the player lacks management access to the org.
        """
        if 'org' in self.arg_parsers:
            if ('org' not in self.parsed_args
                    or self.parsed_args['org'] is None):
                # Org arg, but no org specified. Infer!
                org = self.infer_org()
                if org is None or isinstance(org, tuple):
                    raise self._err('You must specify the organization for '
                                    'this command.')
                else:
                    self.parsed_args['org'] = org
            else:
                org = self.parsed_args['org']
            if self.org_manager and not org.is_manager(self.actor):
                raise self._err('Permission denied.')
        return super(OrgCommand, self).prepare()

    def infer_org(self):
        #: :type: Member
        actor = self.actor
        possible = (actor.managed_orgs if self.org_manager else actor.orgs)
        if len(possible) == 1:
            return possible[0]
        elif len(possible) > 1:
            return possible
        else:
            return None


class OrgsCmd(OrgCommand):
    """
    @orgs [<character>]

    List the organizations you (or the specified player) are a member of.
    """
    aliases = ('@orgs', '@org')
    syntax = '[<char>]'
    arg_parsers = {
        'char': match_char,
    }

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """


class InductCmd(OrgCommand):
    """
    @induct <character> [into <org>]

    Induct the character into an organization you manage.
    """
    aliases = ('@induct',)
    syntax = '<char> [into <org>]'
    arg_parsers = {
        'char': match_char,
        'org': match_org
    }
    org_manager = True

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: Member
        char = args['char']
        #: :type: orgs.Organization
        org = args['org']
        try:
            char.join_org(org)
        except errors.AlreadyInOrg:
            raise self._err('%s is already in %s.' % (actor.name_for(char),
                                                      actor.name_for(org)))
        else:
            actor.tell('{m', char, '{g is now a member of {c', org, '{g.')


class DismissCmd(OrgCommand):
    """
    @dismiss <character> [from <org>]

    Remove a character from an organization you manage.
    """
    aliases = ('@dismiss',)
    syntax = '<char> [from <org>]'
    arg_parsers = {
        'char': match_char,
        'org': match_org
    }
    org_manager = True

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: Member
        char = args['char']
        #: :type: orgs.Organization
        org = args['org']
        try:
            char.leave_org(org)
        except errors.NotInOrg:
            raise self._err('%s is not in %s.' % (actor.name_for(char),
                                                  actor.name_for(org)))
        else:
            actor.tell('{m', char, '{y has been removed from {c', org, '{y.')


Member.private_commands = mudsling.commands.all_commands(sys.modules[__name__])
