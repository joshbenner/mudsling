"""
Player commands.
"""
import time
import traceback

from mudsling.commands import Command
from mudsling.ansi import parse_ansi
from mudsling.objects import Object
from mudsling.utils import string
from mudsling.utils.python import objTreeReplace
from mudsling.errors import MatchError
from mudsling.perms import Role


class EvalCmd(Command):
    """
    @eval <python code>

    Execute arbitrary python code.
    """

    aliases = ('@eval',)
    syntax = "<code>"
    required_perm = "eval code"

    def run(self, this, actor, args):
        """
        Execute and time the code.

        @type actor: mudslingcore.objects.Player
        """

        import mudslingcore
        import sys
        import mudsling.utils

        # args['code'] isn't reliable since the semicolon shortcut may skip
        # parsing the args via syntax.
        code = self.argstr

        #: @type: Object
        char = actor.possessing

        if not code:
            actor.msg(self.syntaxHelp())
            return False

        available_vars = {
            'eval_cmd': self,
            'sys': sys,
            'game': self.game,
            'ref': self.game.db.getRef,
            'player': actor,
            'me': char,
            'here': (char.location if self.game.db.isValid(char, Object)
                     else None),
            'mudslingcore': mudslingcore,
            'utils': mudsling.utils,
        }

        actor.msg("{y>>> %s" % code)

        mode = 'eval'
        duration = compile_time = None
        #noinspection PyBroadException
        try:
            begin = time.clock()
            #noinspection PyBroadException
            try:
                compiled = compile(code, '', 'eval')
            except:
                mode = 'exec'
                compiled = compile(code, '', 'exec')
            compile_time = time.clock() - begin

            begin = time.clock()
            ret = eval(compiled, {}, available_vars)
            duration = time.clock() - begin

            if mode == 'eval':
                ret = "<<< %s" % repr(ret)
            else:
                ret = "<<< Done."
        except:
            error_lines = traceback.format_exc().split('\n')
            if len(error_lines) > 4:
                error_lines = error_lines[4:]
            ret = "\n".join("<<< %s" % line for line in error_lines if line)

        raw_string = parse_ansi("{m") + ret + parse_ansi("{n")
        actor.msg(raw_string, {'raw': True})
        if duration is not None:
            msg = "Exec time: %.3f ms, Compile time: %.3f ms (total: %.3f ms)"
            actor.msg(msg % (duration * 1000,
                             compile_time * 1000,
                             (duration + compile_time) * 1000))


class RolesCmd(Command):
    """
    @roles [<player>]

    List all roles, or display the roles granted to a specified player.
    """
    aliases = ('@roles',)
    syntax = "[<player>]"
    required_perm = 'view perms'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        if not self.argwords:
            # List roles
            msg = "{yRoles: {c%s"
            actor.msg(msg % string.english_list(self.game.db.roles, 'none'))
            return

        matches = actor.matchObjectOfType(self.argstr, cls=Player)
        if self.matchFailed(matches, self.argstr, 'player', show=True):
            return
        player = matches[0]

        msg = ("{yRoles for {c%s{y: {m%s"
               % (player.nn, string.english_list(player.roles, 'none')))
        actor.msg(msg)


class PermsCmd(Command):
    """
    @perms <player>

    List all perms on the specified player.
    """
    aliases = ('@perms',)
    syntax = "<player>"
    required_perm = 'view perms'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        matches = actor.matchObjectOfType(self.argstr, cls=Player)
        if self.matchFailed(matches, self.argstr, 'player', show=True):
            return
        player = matches[0]
        perms = set()
        for role in player.roles:
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
    required_perm = 'view perms'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.matchRole(args['role'])
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
    required_perm = 'manage roles'

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
    required_perm = 'manage roles'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            role = self.game.db.matchRole(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        objTreeReplace(self.game.db, role, None, remove=True)
        actor.msg('Role %s removed from all game objects.' % role.name)


class AddRoleCmd(Command):
    """
    @add-role <role> to <player>

    Adds a role to a player.
    """
    aliases = ('@add-role',)
    syntax = "<role> to <player>"
    required_perm = 'grant roles'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        try:
            role = self.game.db.matchRole(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        matches = actor.matchObjectOfType(args['player'], cls=Player)
        if self.matchFailed(matches, args['player'], 'player', show=True):
            return
        player = matches[0]

        if role in player.roles:
            actor.msg('{c%s {yalready has the {m%s {yrole.'
                      % (player.nn, role.name))
        else:
            player.roles.add(role)
            actor.msg("{c%s {yhas been given the {m%s {yrole."
                      % (player.nn, role.name))


class RemoveRoleCmd(Command):
    """
    @rem-role <role> from <player>

    Removes a role from a player.
    """
    aliases = ('@rem-role',)
    syntax = "<role> from <player>"
    required_perm = 'grant roles'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        from mudslingcore.objects import Player

        try:
            role = self.game.db.matchRole(args['role'])
        except MatchError as e:
            actor.msg(e.message)
            return

        matches = actor.matchObjectOfType(args['player'], cls=Player)
        if self.matchFailed(matches, args['player'], 'player', show=True):
            return
        player = matches[0]

        if role in player.roles:
            player.roles.remove(role)
            actor.msg("{m%s {yrole removed from {c%s{y."
                      % (role.name, player.nn))
        else:
            actor.msg("{c%s {ydoes not have the {m%s {yrole."
                      % (player.nn, role.name))
