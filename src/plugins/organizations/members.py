import sys

import mudsling.commands
import mudsling.objects
import mudsling.parsers
import mudsling.locks

import mudslingcore.ui

import organizations.errors as errors
import organizations.orgs as orgs

manage_orgs = mudsling.locks.Lock('perm(manage orgs)')


class Member(mudsling.objects.BaseCharacter):
    org_memberships = ()

    @property
    def orgs(self):
        return tuple(m.org for m in self.org_memberships)

    @property
    def primary_org(self):
        return self.org_memberships[0].org if self.org_memberships else None

    def set_primary_org(self, org):
        if not self.in_org(org):
            raise errors.NotInOrg()
        others = tuple(m for m in self.org_memberships if m.org != org)
        self.org_memberships = (self.get_org_membership(org),) + others
        self.tell('{c', org, '{n is now your primary organization.')

    @property
    def citizenship(self):
        return tuple(m.org for m in self.org_memberships if m.org.sovereign)

    @property
    def primary_citizenship(self):
        citizenship = self.citizenship
        return citizenship[0] if citizenship else None

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
    ui = mudslingcore.ui.ClassicUI()

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


class CreateOrgCmd(mudsling.commands.Command):
    """
    @create-org[/sovereign] <name> (<abbrev>) [under <parent>]

    Create a new organization.
    """
    aliases = ('@create-org',)
    syntax = '<name> (<abbrev>) [under <parent>]'
    arg_parsers = {
        'parent': match_org,
    }
    switch_defaults = {'sovereign': False}
    switch_parsers = {'sovereign': mudsling.parsers.BoolStaticParser}
    lock = mudsling.locks.Lock('perm(create orgs)')

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        name = args['name']
        abbrev = args['abbrev']
        if len(abbrev) < 2:
            raise self._err('Abbreviations must be at least 2 characters.')
        #: :type: orgs.Organization
        parent = args['parent']
        #: :type: orgs.Organization
        org = orgs.Organization.create(names=(name,), owner=actor)
        org.abbreviation = abbrev
        org.sovereign = self.switches['sovereign']
        if parent:
            org.make_child_org(parent)
        actor.tell('{gCreated ', '{ysovereign {g' if org.sovereign else '',
                   'org {c', org, '{g. Parent: {m', parent, '{g.')


class MakeSuborgCmd(mudsling.commands.Command):
    """
    @make-suborg <org> under <parent>

    Move a suborg to be a child of another org.
    """
    aliases = ('@make-suborg',)
    syntax = '<org> under <parent>'
    arg_parsers = {
        'org': match_org,
        'parent': match_org,
    }
    lock = manage_orgs

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: orgs.Organization
        org = args['org']
        #: :type: orgs.Organization
        parent = args['parent']
        if parent == org.parent_org:
            raise self._err('Specified parentage already in place.')
        try:
            org.make_child_org(parent)
        except errors.RecursiveParentage as e:
            raise self._err(e.message)
        else:
            actor.tell('{c', org, ' {nis now a suborg of {m', parent, '{n.')


class MakeIndependentCmd(mudsling.commands.Command):
    """
    @make-independent <org>

    Make an organization independent.
    """
    aliases = ('@make-independent',)
    syntax = '<org>'
    arg_parsers = {'org': match_org}
    lock = manage_orgs

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: orgs.Organization
        org = args['org']
        if org.parent_org is None:
            raise self._err('Already independent.')
        org.make_independent_org()
        actor.tell('{c', org, '{n is now independent.')


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
        char = args['char'] or actor
        if char != actor and not actor.has_perm('manage orgs'):
            raise self._err('Permission denied.')
        c = self.ui.Column
        table = self.ui.Table([
            c('Organization', align='l',
              cell_formatter=self.org_name_formatter, formatter_args=(char,)),
            c('Rank', align='l', data_key='rank')
        ])
        table.add_rows(*char.org_memberships)
        actor.tell(self.ui.report(
            'Organizations for %s' % actor.name_for(char), table,
            '{y*{n = Primary Org, {gM{n = Organization Manager'))

    def org_name_formatter(self, membership, char):
        out = '{y*{n' if membership.org == char.primary_org else ' '
        out += '{gM{n ' if char in membership.org.managers else '  '
        out += self.actor.name_for(membership.org)
        return out


class PrimaryOrgCmd(OrgCommand):
    """
    @primary-org [for <char> is] <org>

    Sets your primary org. Admin can set primary org for other characters.
    """
    aliases = ('@primary-org',)
    syntax = '[for <char> is] <org>'
    arg_parsers = {
        'char': match_char,
        'org': match_org
    }

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: Member
        char = args['char'] or actor
        #: :type: orgs.Organization
        org = args['org']
        if char != actor and not actor.has_perm('manage orgs'):
            raise self._err('Permission denied.')
        if char.primary_org == org:
            raise self._err('%s is already the primary organization.'
                            % actor.name_for(org))
        try:
            char.set_primary_org(org)
        except errors.NotInOrg:
            raise self._err('Must be a member of org to set it as primary.')
        else:
            actor.tell('{c', org, '{n is now the primary org for {m', char,
                       '{n.')


class SuborgsCmd(OrgCommand):
    """
    @suborgs[/all] <org>

    Display the org and its suborgs. The /all switch will show a all levels.
    """
    aliases = ('@suborgs',)
    syntax = '<org>'
    arg_parsers = {'org': match_org}
    switch_defaults = {'all': False}
    switch_parsers = {'all': mudsling.parsers.BoolStaticParser}

    def run(self, this, actor, args):
        """
        :type this: Member
        :type actor: Member
        :type args: dict
        """
        #: :type: orgs.Organization
        org = args['org']
        all = self.switches['all']
        out = [actor.name_for(org)]
        out.extend(self.suborgs(org, descend=all))
        actor.tell('\n'.join(out))

    def suborgs(self, org, descend, depth=1):
        """
        :type org: orgs.Organization
        :type descend: bool
        :rtype: list
        """
        out = []
        name = self.actor.name_for
        for suborg in org.child_orgs:
            out.append('  ' * depth + name(suborg))
            if descend:
                out.extend(self.suborgs(suborg, True, depth + 1))
        return out


class ParentOrgsCmd(OrgCommand):
    """
    @parent-orgs <org>

    Display the parentage of the specified organization.
    """
    aliases = ('@parent-orgs',)
    syntax = '<org>'
    arg_parsers = {'org': match_org}

    def run(self, this, actor, args):
        #: :type: orgs.Organization
        org = args['org']
        parentage = [actor.name_for(o) for o in org.org_parentage]
        parentage.reverse()
        parentage.append('{c' + actor.name_for(org))
        out = []
        indent = 0
        for o in parentage:
            out.append('  ' * indent + o)
            indent += 1
        actor.tell('\n'.join(out))


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
