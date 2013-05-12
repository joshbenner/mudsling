"""
Administrative commands for managing players.
"""
import re
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
    @ban[/ip] <player or IP> [for <duration>] [because <reason>]

    Ban a player from logging in for an optional duration. If no duration is
    given, the ban does not expire. A reason may also be provided.
    """
    aliases = ('@ban',)
    syntax = ("<what> {for ever|forever} [{due to|because} <reason>]",
              "<what> [for <duration>] [{due to|because} <reason>]",)
    lock = "perm(ban)"
    arg_parsers = {
        'what': parsers.MatchDescendants(cls=BasePlayer,
                                         search_for='player',
                                         show=True),
        'duration': parsers.DhmsStaticParser,
    }
    switch_parsers = {
        'ip': parsers.BoolStaticParser,
    }
    switch_defaults = {
        'ip': False,
    }

    def parse_switches(self, switchstr):
        """
        Overrides switch parsing so that if the 'ip' switch is used, then the
        arg parser for 'what' is swapped out.
        """
        switches = super(BanCmd, self).parse_switches(switchstr)
        if 'ip' in switches and switches['ip']:
            def parse_ip(ipstr):
                if re.match(r'[.*0-9]+', ipstr):
                    return ipstr
                else:
                    raise errors.ParseError('Invalid IP pattern: %s' % ipstr)
            # Copy from class to instance.
            self.arg_parsers = dict(self.arg_parsers)
            self.arg_parsers['what'] = parse_ip
        return switches

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        what = args['what']

        if self.switches['ip']:
            existing = bans.find_bans(ban_type=bans.IPBan, ip_pattern=what,
                                      is_active=True)
        else:
            existing = bans.find_bans(ban_type=bans.PlayerBan, player=what,
                                      is_active=True)
        if existing:
            if len(existing) > 1:
                actor.tell('{m', what, "{y already has multiple bans!")
            else:
                expires = existing[0].expires
                if expires is None:
                    actor.tell('{m', what, "{y is already banned forever.")
                    return
                actor.tell('{m', what, "{y is already banned until {c",
                           utils.time.format_timestamp(expires, 'long'))
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
        what = args['what']
        actor = self.actor
        if 'duration' in args:
            expires = time.time() + args['duration']
            prompt = ["{yYou want to ban {m", what, "{y until {c",
                      utils.time.format_timestamp(expires, 'long'), "{y?"]
        else:
            expires = None
            prompt = ["{yYou want to ban {m", what, "{c indefinitely{y?"]
        self.expires = expires
        actor.tell(*prompt)
        actor.prompt_yes_no(yes_callback=self._really_do_ban,
                            no_callback=self._ban_abort)

    def _really_do_ban(self):
        what = self.parsed_args['what']
        reason = self.parsed_args.get('reason', 'No reason given.')
        kwargs = {'expires': self.expires,
                  'createdBy': self.actor,
                  'reason': reason}
        if self.switches['ip']:
            kwargs['ip_pattern'] = what
            ban_type = bans.IPBan
        else:
            kwargs['player'] = what
            ban_type = bans.PlayerBan
        bans.add_ban(ban_type(**kwargs))
        msg = ["{yYou have banned {m", what]
        if self.expires is None:
            msg.append("{c indefinitely{y.")
        else:
            end = utils.time.format_timestamp(self.expires, 'long')
            msg.extend(["{y until {c", end, "{y."])
        self.actor.tell(*msg)


class UnBanCmd(Command):
    """
    @unban[/ip] <player or IP>

    Unbans the specified player or IP address.
    """
    aliases = ('@unban',)
    syntax = "<what>"
    lock = "perm(ban)"
    arg_parsers = {
        'what': parsers.MatchDescendants(cls=BasePlayer,
                                         search_for='player',
                                         show=True),
    }
    switch_parsers = {
        'ip': parsers.BoolStaticParser,
    }
    switch_defaults = {
        'ip': False,
    }

    def parse_switches(self, switchstr):
        """
        Overrides switch parsing so that if the 'ip' switch is used, then the
        arg parser for 'what' is swapped out.
        """
        switches = super(UnBanCmd, self).parse_switches(switchstr)
        if 'ip' in switches and switches['ip']:
            def parse_ip(ipstr):
                if re.match(r'[.*0-9]+', ipstr):
                    return ipstr
                else:
                    raise errors.ParseError('Invalid IP pattern: %s' % ipstr)
                # Copy from class to instance.
            self.arg_parsers = dict(self.arg_parsers)
            self.arg_parsers['what'] = parse_ip
        return switches

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        what = args['what']
        type = 'IP' if self.switches['ip'] else 'player'

        prompt = "{yExpire all bans on %s {m%s{y?" % (type, what)
        actor.prompt_yes_no(prompt,
                            yes_callback=self._do_unban,
                            no_callback=self._abort_unban)

    def _do_unban(self):
        what = self.parsed_args['what']
        ban_type = bans.IPBan if self.switches['ip'] else bans.PlayerBan
        attr = 'ip_pattern' if self.switches['ip'] else 'player'
        kwargs = {'ban_type': ban_type, attr: what, 'is_active': True}
        bans_to_expire = bans.find_bans(**kwargs)
        now = time.time()
        for ban in bans_to_expire:
            ban.expires = now
        self.actor.tell("{c", len(bans_to_expire), "{g ",
                        'IP' if self.switches['ip'] else 'player',
                        " bans for {m", what, "{g have been manually expired.")

    def _abort_unban(self):
        self.actor.tell("{yUN-ban aborted.")


class BansCmd(Command):
    """
    @bans

    List all active bans.
    """
    aliases = ('@bans',)
    lock = 'perm(manage players) or perm(ban)'

    def run(self, this, actor, args):
        active_bans = bans.find_bans(is_active=True)
        if len(active_bans):
            table = ui.Table([
                ui.Column('Type', data_key='type', align='l'),
                ui.Column('Target', align='l',
                          cell_formatter=self.format_target),
                ui.Column('Expiration', data_key='expires', align='l',
                          cell_formatter=self.format_expiration),
                ui.Column('Reason', data_key='reason', align='l')
            ])
            table.add_rows(*active_bans)
            actor.msg(ui.report('Active Bans', table))
        else:
            actor.tell("{yThere are currently no active bans.")

    def format_expiration(self, expires):
        if expires is None:
            return 'never'
        else:
            return ui.format_timestamp(expires, format='short')

    def format_target(self, ban):
        if isinstance(ban, bans.PlayerBan):
            return self.actor.name_for(ban.player)
        else:
            return ban.what()
