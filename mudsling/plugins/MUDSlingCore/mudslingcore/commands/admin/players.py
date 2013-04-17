"""
Administrative commands for managing players.
"""
from mudsling import parsers
from mudsling import errors
from mudsling.commands import Command
from mudsling.objects import BasePlayer

from mudsling import utils
import mudsling.utils.string

from . import ui


class MakePlayerCmd(Command):
    """
    @make-player <name(s)> [<password>]

    Creates a new player (and corresponding character) registered with the
    given email. Sends the new player an email if the /send switch is used.
    """
    aliases = ('@make-player', '@new-player', '@create-player')
    syntax = "<names> [<password>]"
    lock = 'perm(create players)'
    arg_parsers = {
        'names': parsers.StringListStaticParser,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        playerClass = self.game.player_class
        password = args['password'] or utils.string.randomString(10)

        try:
            newPlayer = playerClass.create(names=args['names'],
                                           password=password,
                                           makeChar=True)
        except errors.Error as e:
            actor.msg("{y%s" % e)
            return

        actor.tell("{gPlayer created: {m", newPlayer,
                   "{g with password '{r", password, "{g'.")
        actor.tell("{gCharacter created: {c", newPlayer.default_object, "{g.")


class NewPasswordCmd(Command):
    """
    @new-password <player> is <new password>

    Changes the password for the specified player.
    """
    aliases = ('@new-password', '@change-password', '@set-password')
    syntax = "<player> {is|to|=} <password>"
    lock = 'perm(manage players)'
    arg_parsers = {
        'player': parsers.MatchDescendants(cls=BasePlayer,
                                           searchFor='player',
                                           show=True),
    }

    def run(self, this, actor, args):
        if not args['password']:
            raise self._err("Password cannot be blank.")
        args['player'].setPassword(args['password'])
        actor.tell("{gPassword for {m", args['player'],
                   "{g updated to '{r", args['password'], "{g'.")


class BootCmd(Command):
    """
    @boot <player> [for <reason>]

    Disconnects the specified player.
    """
    aliases = ('@boot',)
    syntax = "<player> [{for|because|=|due to} <reason>]"
    lock = "perm(boot players)"
    arg_parsers = {
        'player': parsers.MatchDescendants(cls=BasePlayer,
                                           searchFor='player',
                                           show=True),
    }

    def run(self, this, actor, args):
        player = args['player']
        reason = args.get('reason', None) or "No reason given"
        if not player.connected:
            actor.tell("{m", player, "{y is not connected.")
        player.tell("{yYou have been {rbooted{y by {m", actor, "{y.")
        player.session.disconnect("{yReason: {c%s" % reason)
        actor.tell("{yYou have {rbooted {m", player, "{y because: {c", reason)


class ShoutCmd(Command):
    """
    @shout <message>

    Displays the message to all connected players.
    """
    aliases = ('@shout', '@wall')
    syntax = "<message>"
    lock = "perm(shout)"

    def run(self, this, actor, args):
        m = '{m%s {gshouts: "{y%s{g".' % (actor.name, args['message'])
        for conn in self.game.session_handler.sessions:
            conn.sendOutput(m)


class WhoFromCmd(Command):
    """
    @who [<player>]

    Display connection information for the specified player.
    """
    aliases = ('@who', '@@who')
    syntax = "[<player>]"
    lock = "perm(manage players)"
    arg_parsers = {
        'player': parsers.MatchDescendants(cls=BasePlayer,
                                           searchFor='player',
                                           show=True),
    }

    def run(self, this, actor, args):
        if args['player'] is None:
            table = ui.Table([
                ui.Column('Player', data_key='player', align='l',
                          cell_formatter=actor.nameFor),
                ui.Column('IP', data_key='ip', align='l'),
                ui.Column('Host', data_key='hostname', align='l'),
            ])
            table.addRows(*self.game.session_handler.sessions)
            actor.msg(ui.report("Player Connection Info", table))
        else:
            p = args['player']
            if not p.connected:
                actor.tell("{m", p, "{y is not connected.")
            else:
                s = p.session
                actor.tell("{m", p, "{n is connected from IP {y", s.ip,
                           "{n ({c", s.hostname, "{n)")


class BanCmd(Command):
    """
    @ban <player> [for <duration>]
    """
