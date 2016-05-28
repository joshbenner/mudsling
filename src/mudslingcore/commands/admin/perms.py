from mudsling.commands import Command
from mudsling.utils import string
from mudsling.errors import MatchError
from mudsling.perms import Role


class RolesCmd(Command):
    """
    @roles [<player>]

    List all roles, or display the roles granted to a specified player.
    """
    aliases = ('@roles',)
    syntax = "[<player>]"
    lock = 'perm(view perms)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        if not self.argwords:
            # List roles
            msg = "{yRoles: {m%s"
            actor.msg(msg % string.english_list(self.game.db.roles, 'none'))
            return

        matches = actor.match_obj_of_type(self.argstr, cls=Player)
        if self.match_failed(matches, self.argstr, 'player', show=True):
            return
        player = matches[0]

        msg = ("{yRoles for {c%s{y: {m%s"
               % (player.nn, string.english_list(player.get_roles(), 'none')))
        actor.msg(msg)


class PermsCmd(Command):
    """
    @perms <player>

    List all perms on the specified player.
    """
    aliases = ('@perms',)
    syntax = "<player>"
    lock = 'perm(view perms)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        matches = actor.match_obj_of_type(self.argstr, cls=Player)
        if self.match_failed(matches, self.argstr, 'player', show=True):
            return
        #: @type: Player
        player = matches[0]
        perms = set()
        for role in player.get_roles():
            perms |= role.perms
        perms = string.english_list(perms)

        msg = "{yPerms for {c%s{y: {g%s"
        actor.msg(msg % (player.nn, perms))


class ShowRoleCmd(Command):
    """
    @show-role <role>

    Display the perms that are granted to the specified role.
    """
    aliases = ('@show-role',)
    syntax = "<role>"
    lock = 'perm(view perms)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        msg = "{yPermissions for role {m%s{y: {g%s"
        perms = string.english_list(role.perms, nothingstr="No perms")
        actor.msg(msg % (role.name, perms))


class CreateRoleCmd(Command):
    """
    @create-role <role>

    Creates a new role.
    """
    aliases = ('@create-role',)
    syntax = "<role>"
    lock = 'perm(manage roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        for role in self.game.db.roles:
            if role.name == args['role']:
                actor.msg("{rThere is already a role named '%s'" % role.name)
                return

        role = Role(args['role'])
        self.game.db.roles.append(role)
        actor.msg("{gCreated new role: {m%s" % role.name)


class DeleteRoleCmd(Command):
    """
    @del-role <role>

    Deletes a role.
    """
    aliases = ('@del-role',)
    syntax = "<role>"
    lock = 'perm(manage roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        self.game.db.expunge_role(role)
        actor.msg('{rRole {m%s {rhas been deleted.' % role.name)


class AddRoleCmd(Command):
    """
    @add-role <role> to <player>

    Adds a role to a player.
    """
    aliases = ('@add-role',)
    syntax = "<role> to <player>"
    lock = 'perm(grant roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        matches = actor.match_obj_of_type(args['player'], cls=Player)
        if self.match_failed(matches, args['player'], 'player', show=True):
            return
        player = matches[0]

        if player.has_role(role):
            actor.msg('{c%s {yalready has the {m%s {yrole.'
                      % (player.nn, role.name))
        else:
            player.add_role(role)
            actor.msg("{c%s {yhas been given the {m%s {yrole."
                      % (player.nn, role.name))


class RemoveRoleCmd(Command):
    """
    @rem-role <role> from <player>

    Removes a role from a player.
    """
    aliases = ('@rem-role',)
    syntax = "<role> from <player>"
    lock = 'perm(grant roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        matches = actor.match_obj_of_type(args['player'], cls=Player)
        if self.match_failed(matches, args['player'], 'player', show=True):
            return
        player = matches[0]

        if player.has_role(role):
            player.remove_role(role)
            actor.msg("{m%s {yrole removed from {c%s{y."
                      % (role.name, player.nn))
        else:
            actor.msg("{c%s {ydoes not have the {m%s {yrole."
                      % (player.nn, role.name))


class AddPermCmd(Command):
    """
    @add-perm <perm> to <role>

    Adds a permission to a role.
    """
    aliases = ('@add-perm',)
    syntax = "<perm> to <role>"
    lock = 'perm(manage roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        if role.add_perm(args['perm']):
            actor.msg("{g%s {yadded to {m%s{y.", (args['perm'], role))
        else:
            actor.msg("{m%s {yalready has the {g%s {ypermission."
                      % (role, args['perm']))


class RemovePermCmd(Command):
    """
    @rem-perm <perm> from <role>

    Remove a permission from a role.
    """
    aliases = ('@rem-perm',)
    syntax = "<perm> from <role>"
    lock = 'perm(manage roles)'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.match_role(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        if role.remove_perm(args['perm']):
            actor.msg("{g%s {yremoved from {m%s{y." % (args['perm'], role))
        else:
            actor.msg("{m%s {ydoes not have the {g%s {ypermission."
                      % (role, args['perms']))
