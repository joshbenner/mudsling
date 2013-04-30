"""
Administrative commands for managing players.
"""
import time

from mudsling import parsers
from mudsling import errors
from mudsling.commands import Command
from mudsling.objects import BasePlayer

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.time

from . import ui
from mudslingcore import bans


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
        password = args['password'] or utils.string.random_string(10)

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
                                           search_for='player',
                                           show=True),
    }

    def run(self, this, actor, args):
        if not args['password']:
            raise self._err("Password cannot be blank.")
        args['player'].set_password(args['password'])
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
                                           search_for='player',
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
            conn.send_output(m)


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
                                           search_for='player',
                                           show=True),
    }

    def run(self, this, actor, args):
        if args['player'] is None:
            table = ui.Table([
                ui.Column('Player', data_key='player', align='l',
                          cell_formatter=actor.name_for),
                ui.Column('IP', data_key='ip', align='l'),
                ui.Column('Host', data_key='hostname', align='l'),
            ])
            table.add_rows(*self.game.session_handler.sessions)
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
    @ban <player> [for <duration>] [because <reason>]

    Ban a player from logging in for an optional duration. If no duration is
    given, the ban does not expire. A reason may also be provided.
    """
    aliases = ('@ban', '@ban-player')
    syntax = ("<player> {for ever|forever} [{due to|because} <reason>]",
              "<player> [for <duration>] [{due to|because} <reason>]",)
    lock = "perm(ban)"
    arg_parsers = {
        'player': parsers.MatchDescendants(cls=BasePlayer,
                                           search_for='player',
                                           show=True),
        'duration': parsers.DhmsStaticParser,
    }
    format = "%g:%i%a on %l, %F %j%S %Y"

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        player = args['player']
        existing = bans.find_bans(type=bans.PlayerBan, player=player)
        if existing:
            if len(existing) > 1:
                actor.tell('{m', player, "{y already has multiple bans!")
            else:
                expires = existing[0].expires
                if expires is None:
                    actor.tell('{m', player,
                               "{y is already banned indefinitely.")
                    return
                actor.tell('{m', player, "{y is already banned until {c",
                           utils.time.format_timestamp(expires, self.format))
            prompt = "{yAre you sure you want to impose an additional ban?"
            actor.prompt_yes_no(prompt,
                                yes_callback=self._prompt_for_ban,
                                no_callback=self._ban_abort)
        else:
            self._prompt_for_ban()

    def _ban_abort(self):
        self.actor.msg('{gBanning aborted.')

    def _prompt_for_ban(self):
        args = self.parsed_args
        player = args['player']
        actor = self.actor
        if 'duration' in args:
            expires = utils.time.utctime() + args['duration']
            prompt = ["{yYou want to ban {m", player, "{y until {c",
                      utils.time.format_timestamp(expires, self.format), "{y?"]
        else:
            expires = None
            prompt = ["{yYou want to ban {m", player, "{c indefinitely{y?"]
        self.expires = expires
        actor.tell(*prompt)
        actor.prompt_yes_no(yes_callback=self._really_do_ban,
                            no_callback=self._ban_abort)

    def _really_do_ban(self):
        player = self.parsed_args['player']
        reason = self.parsed_args.get('reason', 'No reason given.')
        bans.add_ban(bans.PlayerBan(player=player,
                                    expires=self.expires,
                                    createdBy=self.actor,
                                    reason=reason))
        msg = ["{yYou have banned {m", player]
        if self.expires is None:
            msg.append("{c indefinitely{y.")
        else:
            end = utils.time.format_timestamp(self.expires, self.format)
            msg.extend(["{y until {c", end, "{y."])
        self.actor.tell(*msg)
