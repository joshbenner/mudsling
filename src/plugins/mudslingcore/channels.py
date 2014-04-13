"""
MUDSlingCore channel system.
"""
import logging
import re
import sqlite3
import os

from mudsling.objects import NamedObject, BaseObject
from mudsling import locks
from mudsling.commands import Command, CommandSet
from mudsling.parsers import BoolStaticParser, MatchDescendants
from mudsling import errors

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.file as file_utils
import mudsling.utils.db as db_utils
import mudsling.utils.time as time_utils

import mudslingcore
from mudslingcore.ui import ClassicUI

ui = ClassicUI()


class ChannelWhoCmd(Command):
    """
    <alias> /who

    Displays list of participants on the channel.
    """
    aliases = ('who',)
    lock = locks.all_pass

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        names = map(lambda p: actor.name_for(p), chan.participants)
        msg = "Participants: %s" % utils.string.english_list(names)
        chan.tell(actor, msg)


class ChannelAllowCmd(Command):
    """
    <alias> /allow <lock expression>

    Restrict who may join a channel.
    """
    aliases = ('allow', 'lock')
    syntax = "<lock>"
    lock = 'operator()'

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        lock_expr = args['lock']
        if lock_expr in ('invited', 'invitees', 'invite'):
            lock_expr = 'invited()'
        elif lock_expr in ('all', 'everyone', 'everybody'):
            lock_expr = 'all()'
        lock = locks.Lock(lock_expr)
        try:
            # Test evaluation to make sure it works.
            lock.eval(chan, actor)
        except:
            logging.exception("Eval lock: %s" % lock_expr)
            chan.tell(actor, "{rInvalid lock expression.")
        else:
            chan.set_lock('join', lock_expr)
            chan.tell(actor, "{yJoin lock set to: {c", chan.get_lock('join'))


class ChannelOnCmd(Command):
    """
    <alias> /on

    Begin listening to the channel.
    """
    aliases = ('on', 'unmute', 'join')
    lock = locks.all_pass

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        if actor in chan.participants:
            chan.tell(actor, "{yYou are already on this channel.")
        elif not chan.joinable_by(actor):
            chan.tell(actor, "{rYou are not allowed to join this channel.")
        else:
            chan.joined_by(actor)


class ChannelOffCmd(Command):
    """
    <alias> /off

    Stop listening to the channel.
    """
    aliases = ('off', 'mute', 'leave')
    lock = locks.all_pass

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        if actor not in chan.participants:
            chan.tell(actor, "{yYou are not on this channel.")
        else:
            chan.left_by(actor)


class ChannelOpCmd(Command):
    """
    <alias> /op <player> [on|off]

    Flag the player as a channel operator.
    """
    aliases = ('op', 'operator', 'operators', 'admin')
    syntax = "<player> [{on|off}]"
    lock = 'operator()'

    def __init__(self, *args, **kwargs):
        # Avoid circular reference issues.
        self.arg_parsers = {
            'player': MatchDescendants(cls=ChannelUser, search_for='player',
                                       show=True),
        }
        super(ChannelOpCmd, self).__init__(*args, **kwargs)

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        toggle = args.get('optset1', None)
        player = args['player']
        if toggle is None:
            status = ("an {goperator{n" if player in chan.operators
                      else "{rnot {nan operator")
            chan.tell(actor, player, ' is ', status, '.')
        elif toggle == 'on':
            if player in chan.operators:
                chan.tell(actor, '{c', player, " {yis already an operator.")
            else:
                chan.operators.add(player)
                chan.tell(actor, '{c', player, " {gis now an operator.")
                chan.tell(player, "{gYou are now an operator.")
        else:
            if player not in chan.operators:
                chan.tell(actor, '{c', player, " {yis not an operator.")
            else:
                chan.operators.remove(player)
                chan.tell(actor, '{c', player, " {yis no longer an operator.")
                chan.tell(player, "{yYou are no longer an operator.")


class ChannelVoiceCmd(Command):
    """
    <alias> /voice [all|<player> [on|off]]

    Give/take voice, or display who currently has voice.
    """
    aliases = ('voice',)
    syntax = (
        "all {on|off}",
        "[<player> [{on|off}]]"
    )
    lock = 'operator()'

    def __init__(self, *args, **kwargs):
        # Avoid circular reference issues.
        self.arg_parsers = {
            'player': MatchDescendants(cls=ChannelUser, search_for='player',
                                       show=True),
        }
        super(ChannelVoiceCmd, self).__init__(*args, **kwargs)

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        if 'optset1' in args:
            mode = args['optset1']
            if args['player'] is not None:
                player = args['player']
                msg = self._set_player_voice(chan, actor, player, mode)
            else:
                # No player, but optset1... that means we are acting on ALL.
                msg = self._set_all_voice(chan, actor, mode)
        else:  # No on/off.
            if args['player'] is not None:
                msg = self._show_player_voice(chan, actor, args['player'])
            else:
                # No on/off, no player... show all voice info!
                msg = self._show_all_voice(chan, actor)
        chan.tell(actor, '{mVOICE: {n', msg)

    def _set_player_voice(self, chan, actor, player, mode):
        if chan.voice is None:
            msg = "{yCannot grant voice when channel allows all to speak."
        else:
            if mode == 'on':
                if player in chan.voice:
                    msg = "{c%s {yalready has voice."
                else:
                    chan.voice.add(player)
                    msg = "{c%s {nis now {gallowed {nto speak."
            else:
                if player in chan.voice:
                    chan.voice.remove(player)
                    msg = "{c%s {nis now {rNOT allowed {nto speak."
                else:
                    msg = "{c%s {nis already {rNOT allowed {nto speak."
            msg = msg % actor.name_for(player)
        return msg

    def _show_player_voice(self, chan, actor, player):
        if chan.voice is None:
            # Everyone can speak, so use same messaging.
            msg = self._show_all_voice(chan, actor)
        else:
            if player in chan.voice:
                msg = "{c%s {gis allowed {nto speak on this channel."
            else:
                msg = "{c%s {ris NOT allowed {nto speak on this channel."
            msg = msg % actor.name_for(player)
        return msg

    def _set_all_voice(self, chan, actor, mode):
        if mode == 'on':
            if chan.voice is None:
                msg = "{yEveryone can already speak on this channel."
            else:
                chan.voice = None
                msg = "{gEveryone may now speak on this channel."
        else:
            if chan.voice == set():
                msg = "{yEveryone is already silent on this channel."
            else:
                chan.voice = set()
                msg = "{rEveryone has been silenced."
        return msg

    def _show_all_voice(self, chan, actor):
        if chan.voice is None:
            msg = "{gAnyone may speak on this channel."
        else:
            voices = map(actor.name_for, chan.voice)
            voices = utils.string.english_list(voices, nothingstr="Nobody")
            msg = "Voices: %s" % voices
        return msg


class ChannelTopicCmd(Command):
    """
    <alias> /topic <text>

    Set the topic of the channel.
    """
    aliases = ('topic', 'subject')
    syntax = "<text>"
    lock = 'operator()'

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        chan.topic = args['text']
        chan.broadcast("{gTopic set: {n%s" % chan.topic, actor)


class ChannelPrivateCmd(Command):
    """
    <alias> /private [yes|no]

    Sets the channel private (or not).
    """
    aliases = ('private', 'hidden', 'hide')
    syntax = "[{yes|no|on|off}]"
    arg_parsers = {
        'optset1': BoolStaticParser,
    }
    lock = 'operator()'

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        mode = args.get('optset1', None)
        status = lambda c: "{rPRIVATE" if c.private else "{gPUBLIC"
        if mode is None:
            # Display privacy status.
            chan.tell(actor, "{yChannel currently: ", status(chan))
        elif mode:  # Works because of BoolStaticParser
            if chan.private:
                chan.tell(actor, "{yChannel is already ", status(chan))
            else:
                chan.private = True
                chan.tell(actor, "{yChannel is now ", status(chan))
        else:
            if chan.private:
                chan.private = False
                chan.tell(actor, "{yChannel is now ", status(chan))
            else:
                chan.tell(actor, "{yChannel is already ", status(chan))


class ChannelBootCmd(Command):
    """
    <alias> /boot <player> [for <reason>]

    Boots a player from the channel.
    """
    aliases = ('boot', 'kick')
    syntax = "<player> [{for |because } <reason>]"
    lock = 'operator()'

    def __init__(self, *args, **kwargs):
        # Avoid circular reference issues.
        self.arg_parsers = {
            'player': MatchDescendants(cls=ChannelUser, search_for='player',
                                       show=True),
        }
        super(ChannelBootCmd, self).__init__(*args, **kwargs)

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        player = args['player']
        if player in chan._participants:  # Can boot even if offline.
            reason = args.get('reason', None) or None
            if reason is not None:
                chan.tell(player, "{c", actor,
                          "{n has {rbooted {nyou because: {y", reason)
            else:
                chan.tell(player, "{c", actor, "{n has {rbooted {nyou.")
            chan.left_by(player)
            chan.tell(actor, "{yYou have booted {c", player)
        else:
            chan.tell(actor, "{c", player, "{y is not on this channel.")


class ChannelInfoCmd(Command):
    """
    <alias> /info

    Display some information about the channel.
    """
    aliases = ('info',)
    lock = locks.all_pass

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        if chan.voice is None:
            voice = 'Everyone'
        else:
            voices = map(actor.name_for, chan.voice)
            voice = utils.string.english_list(voices, nothingstr="Nobody")
        ops = map(actor.name_for, chan.operators)
        ops = utils.string.english_list(ops, nothingstr="Nobody")
        log = '{rENABLED' if chan.log_enabled else '{gdisabled'
        # noinspection PyListCreation
        msg = [
            'Channel info:',
            '    Topic: %s' % chan.topic or "Not set",
            '    Voice: %s' % voice,
            '  Private: %s' % ('{rYes' if chan.private else '{gNo'),
            '  Logging: %s' % log,
            'Join Lock: %s' % chan.get_lock('join'),
            'Operators: %s' % ops,
        ]
        for line in msg:
            chan.tell(actor, line)


class ChannelInviteCmd(Command):
    """
    <alias> /invite [<player>]

    Invite a player to the channel, or display the list of invited players.
    """
    aliases = ('invite',)
    syntax = '[<player>]'
    lock = 'operator()'

    def __init__(self, *args, **kwargs):
        # Avoid circular reference issues.
        self.arg_parsers = {
            'player': MatchDescendants(cls=ChannelUser, search_for='player',
                                       show=True),
        }
        super(ChannelInviteCmd, self).__init__(*args, **kwargs)

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        player = args.get('player', None)
        if player is None:
            # Display list of invitees.
            invitees = utils.string.english_list(
                actor.list_of_names(chan.invitees), nothingstr="Nobody")
            chan.tell(actor, '{mInvitees: {n', invitees)
        else:
            if player in chan.invitees:
                chan.tell(actor, '{c', player, "{y is already invited.")
            else:
                chan.invitees.add(player)
                chan.tell(player, '{c', actor,
                          "{g has invited you to this channel.")
                chan.tell(actor, '{c', player, "{g has been invited.")


class ChannelUninviteCmd(Command):
    """
    <alias> /uninvite <player>

    Cancel an invitation to a player to join the channel.
    """
    aliases = ('uninvite',)
    syntax = '<player>'
    lock = 'operator()'

    def __init__(self, *args, **kwargs):
        # Avoid circular reference issues.
        self.arg_parsers = {
            'player': MatchDescendants(cls=ChannelUser, search_for='player',
                                       show=True),
        }
        super(ChannelUninviteCmd, self).__init__(*args, **kwargs)

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        player = args['player']
        if player in chan.invitees:
            chan.invitees.remove(player)
            chan.tell(actor, '{c', player, '{y has been UNinvited.')
        else:
            chan.tell(actor, '{c', player, '{r is not invited.')


class ChannelLogCmd(Command):
    """
    <alias> /log on|off

    Enable or disable logging on the channel.
    """
    aliases = ('log',)
    syntax = '{on|off}'
    lock = 'operator()'

    def run(self, chan, actor, args):
        """
        :type chan: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        enable = (args['optset1'] == 'on')
        if enable == chan.log_enabled:
            chan.tell(actor, 'Logging already ',
                      'enabled' if enable else 'disabled', '.')
        else:
            chan.log_enabled = enable
            msg = 'This channel is now '
            msg += '{rON THE RECORD' if enable else '{gOFF THE RECORD'
            chan.broadcast(msg, who=actor)


class Channel(NamedObject):
    """
    Channel object stores the state/config for a channel in the game, the list
    of participants, and processes/routes messages to/from those participants.

    :ivar operators: Players who can administer the channel.
    :ivar _participants: Players who are joined to the channel.
    :ivar invitees: Players who have been invited to the (restricted) channel.
    :ivar voice: If None, all can speak. Otherwise, set of participants that
        can speak on the channel.
    :type voice: None or set
    :ivar private: Whether or not channel is private (hidden).
    :ivar topic: The topic/subject matter of the channel.
    :ivar log: Whether logging is enabled or not.
    """
    operators = set()
    _participants = set()
    invitees = set()
    voice = None
    locks = locks.LockSet('join:all()')
    private = False
    topic = ''
    _log_enabled = False

    _logfile = None
    _transient_vars = ['_logfile']

    commands = CommandSet([
        ChannelWhoCmd,
        ChannelAllowCmd,
        ChannelOnCmd,
        ChannelOffCmd,
        ChannelOpCmd,
        ChannelVoiceCmd,
        ChannelTopicCmd,
        ChannelPrivateCmd,
        ChannelBootCmd,
        ChannelInfoCmd,
        ChannelInviteCmd,
        ChannelUninviteCmd,
        ChannelLogCmd,
    ])

    def __init__(self, **kwargs):
        super(Channel, self).__init__(**kwargs)
        self.operators = set()
        self._participants = set()
        self.invitees = set()

    @property
    def prefix(self):
        return ''.join(['[', self.name, '] '])

    @property
    def participants(self):
        return [p for p in self._participants
                if self.db.is_valid(p, cls=ChannelUser) and p.connected]

    def on_object_deleted(self):
        self.broadcast("{rChannel being deleted...")
        self.locks = locks.LockSet('join:none()')
        self.private = True
        for p in set(self._participants):  # Copy becase we are deleting...
            try:
                p.remove_channel(p.channel_alias(self))
            except:
                logging.exception('Error removing channel from %r' % p)

    def _prepare_message(self, msg):
        if isinstance(msg, tuple):
            msg = list(msg)
        elif isinstance(msg, basestring):
            msg = [msg]
        prefix = self.prefix
        out = []
        for line in msg:
            out.append(prefix + line)
        return '\n'.join(out)

    def broadcast(self, msg, who=None):
        msg = self._prepare_message(msg)
        for p in self.participants:
            try:
                p.msg(msg)
            except Exception:
                logging.warning("Bad object on chan %s: %r" % (self.name, p))
        self.log(who, msg)

    def tell(self, who, *msg):
        msg = self._prepare_message(who._format_msg(msg))
        who.msg(msg)

    def add_operator(self, who):
        self.operators.add(who.ref())

    def joinable_by(self, who):
        who = who.ref()
        return self.allows(who, 'join') or who in self.operators

    def speakable_by(self, who):
        who = who.ref()
        if who in self.participants:
            if self.voice is None or who in self.voice:
                return True
        if who in self.operators:
            return True
        return False

    def joined_by(self, who):
        self._participants.add(who.ref())
        self.broadcast(who.channel_name + ' has joined this channel.')

    def left_by(self, who):
        self.broadcast(who.channel_name + ' has left this channel.')
        self._participants.remove(who.ref())

    def process_input(self, input, who):
        if input.startswith('/'):
            self.process_command(input, who)
        elif self.voice is None or who in self.voice:
            if not who in self._participants:
                raise errors.AccessDenied("You must join the channel first.")
            msg = who.name
            if input.startswith(':'):
                input = input[1:]
                if input.startswith(':'):
                    input = input[1:]
                    msg += input
                else:
                    msg += ' ' + input
            else:
                msg += ': ' + input
            self.broadcast(msg, who)
        else:
            raise errors.AccessDenied('You cannot speak on this channel.')

    def process_command(self, input, actor):
        cmdstr, sep, argstr = input[1:].partition(' ')
        matches = self.commands.match(cmdstr, self.ref(), actor)
        if len(matches) == 1:
            cls = matches[0]
        elif len(matches) > 1:
            raise errors.AmbiguousMatch("Ambiguous channel command.",
                                        query=cmdstr, matches=matches)
        else:
            raise errors.FailedMatch("Invalid command.", query=cmdstr)
        #: :type: mudsling.commands.Command
        cmd = cls(input, cmdstr, argstr, game=self.game, obj=self.ref(),
                  actor=actor)
        if not cmd.match_syntax(argstr):
            self.tell(actor, *cmd.syntax_help().split('\n'))
        else:
            cmd.execute()

    @property
    def log_enabled(self):
        return self._log_enabled

    @log_enabled.setter
    def log_enabled(self, val):
        self._log_enabled = val
        if val and self._logfile is None:
            self._init_logfile()
        elif not val and self._logfile:
            self._logfile.commit()
            self._logfile.close()
            self._logfile = None

    @property
    def log_filename(self):
        return file_utils.sanitize_filename('%s-%d.sqlite' % (self.name,
                                                              self.obj_id))

    @property
    def log_filepath(self):
        return self.game.game_file_path(os.path.join('channel_logs',
                                                     self.log_filename))

    def _init_logfile(self):
        if self._logfile is None:
            filepath = self.log_filepath
            if not os.path.exists(filepath):
                try:
                    self.game.makedirs('channel_logs')
                except OSError:
                    # It probably already exists...
                    pass
                conn = sqlite3.connect(filepath)
                conn.close()
            # Apply any pending migrations.
            module_root = os.path.dirname(mudslingcore.__file__)
            migrations = os.path.join(module_root, 'schemas', 'channel_log')
            db_utils.migrate('sqlite:///%s' % filepath, migrations)
            self._logfile = sqlite3.connect(filepath)

    def log(self, source, text):
        if self._log_enabled:
            self._init_logfile()
            if hasattr(source, 'obj_id'):
                if hasattr(source, 'name'):
                    source = '%s (#%d)' % (source.name, source.obj_id)
                else:
                    source = '#%d' % source.obj_id
            else:
                source = str(source)
            lines = [''.join(l.split(self.prefix, 1))
                     for l in text.splitlines()]
            logfile = self._logfile
            for line in lines:
                logfile.execute('INSERT INTO log (timestamp, source, text)'
                                'VALUES (?, ?, ?)',
                                (time_utils.unixtime(), source, line))
            logfile.commit()


class ChannelsCmd(Command):
    """
    @channels[/all]

    Show a list of channels. The all switch shows all channels accessible to
    the player, while the default is to just show channels the player has
    added to their list of aliases.
    """
    aliases = ('@channels',)
    switch_parsers = {
        'all': BoolStaticParser,
    }
    switch_defaults = {
        'all': False,
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.ChannelUser
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        if self.switches['all']:
            my_channels = actor.channels.values()
            channels = actor.channels.items()
            for channel in self.game.db.descendants(Channel):
                if channel not in my_channels:
                    if (not channel.private
                            or actor in channel.operators
                            or actor in channel.invitees):
                        channels.append((None, channel))
        else:
            channels = actor.channels.items()

        if not channels:
            actor.msg('{yNo channels!')
            return

        rows = []
        for alias, channel in sorted(channels, key=lambda c: c[0]):
            rows.append([
                alias or '',
                channel.name,
                str(len(channel.participants)),
                '{gON' if actor in channel._participants else '{roff',
                channel.topic
            ])

        table = ui.Table([
            ui.Column('Alias'),
            ui.Column('Channel', align='l'),
            ui.Column('#', align='r'),
            ui.Column('Status'),
            ui.Column('Topic', align='l'),
        ])
        table.add_rows(*rows)
        actor.msg(ui.report('Channels', table))


class ChanCreateCmd(Command):
    """
    @chancreate[/private] <channel>

    Create a new channel.
    """
    aliases = ('@chancreate', '@createchan', '@mkchan')
    syntax = '<channel>'
    lock = 'perm(create channels)'
    switch_parsers = {
        'private': BoolStaticParser,
    }
    switch_defaults = {
        'private': False,
    }

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.ChannelUser
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        existing = self.game.db.match_descendants(args['channel'], Channel,
                                                  exactOnly=True)
        if existing:
            actor.msg('{yChannel `{c%s{y` already exists.' % existing[0].name)
        else:
            #: :type: Channel
            channel = Channel.create(names=(args['channel'],))
            if self.switches['private']:
                channel.private = True
            channel.add_operator(actor)
            actor.msg('{gChannel created: {c%s' % channel.name)


class ChanDelCmd(Command):
    """
    @chandel <channel>

    Deletes a channel.
    """
    aliases = ('@chandel', '@delchan')
    syntax = '<channel>'
    arg_parsers = {
        'channel': MatchDescendants(cls=Channel, search_for='channel',
                                    show=True)
    }
    lock = 'perm(delete channels)'

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.ChannelUser
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        name = actor.name_for(args['channel'])
        args['channel'].delete()
        actor.tell('{c', name, '{r deleted.')


class ChanAddCmd(Command):
    """
    @chanadd <channel>=<alias>

    Adds a channel to your personal channel aliases.
    """
    aliases = ('@chanadd', '@addchan')
    syntax = '<channel> {=} <alias>'
    arg_parsers = {
        'channel': MatchDescendants(cls=Channel, search_for='channel',
                                    show=True)
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.ChannelUser
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        try:
            actor.add_channel(args['channel'], args['alias'])
        except (ValueError, errors.AccessDenied) as e:
            actor.msg('{y' + e.message)


class ChanRemoveCmd(Command):
    """
    @chanremove <alias>

    Removes a channel from your personal aliases.
    """
    aliases = ('@chanremove', '@chanrem', '@remchan', '@rmchan')
    syntax = '<alias>'
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.ChannelUser
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        alias = args['alias'].strip()
        if alias not in this.channels:
            raise errors.FailedMatch(msg="No channel alias '%s'." % alias)
        channel = actor.channels[alias]
        actor.remove_channel(alias)
        actor.tell("{yChannel {c", channel, "{y removed.")


class UseChannelCmd(Command):
    """
    Command that is instantiated whenever a user's unmatched input matches a
    channel alias they have registered, and passes the command on to the
    channel itself.
    """
    def run(self, this, actor, args):
        """
        :type this: mudslingcore.channels.Channel
        :type actor: mudslingcore.channels.ChannelUser
        :type args: dict
        """
        try:
            this.process_input(self.argstr, actor)
        except (errors.MatchError, errors.AccessDenied) as e:
            this.tell(actor, '{r%s' % e.message)


class ChannelUser(BaseObject):
    private_commands = [
        ChannelsCmd,
        ChanCreateCmd,
        ChanDelCmd,
        ChanAddCmd,
        ChanRemoveCmd,
    ]

    def __init__(self, **kwargs):
        super(ChannelUser, self).__init__(**kwargs)
        self.channels = {}

    @property
    def channel_name(self):
        return self.name

    def handle_unmatched_input(self, raw):
        cmd = super(ChannelUser, self).handle_unmatched_input(raw)
        if not cmd:
            alias, sep, msg = raw.partition(' ')
            if alias in self.channels:
                cmd = UseChannelCmd(raw, alias, msg.strip(), game=self.game,
                                    obj=self.channels[alias], actor=self.ref())
                return cmd
        return None

    def channel_alias(self, channel):
        channel = channel.ref()
        for a, c in self.channels.iteritems():
            if c == channel:
                return a
        return None

    def has_channel(self, channel):
        return True if self.channel_alias(channel) is not None else False

    def add_channel(self, channel, alias, autojoin=True):
        if not re.match(r'[a-zA-Z0-9][-_a-zA-Z0-9]+', alias):
            msg = ['{yChannel names must begin with a letter or number, ',
                   'and may only contain letters, numbers, underscores, ',
                   'and hyphens.']
            raise ValueError(''.join(msg))
        elif alias in self.channels:
            raise ValueError('Alias `%s` already in use.' % alias)
        elif self.has_channel(channel):
            a = self.channel_alias(channel)
            msg = 'Channel %s already added with as `%s`.' % (channel.name, a)
            raise ValueError(msg)
        elif not channel.joinable_by(self):
            raise errors.AccessDenied('Cannot join channel %s.' % channel.name)
        else:
            if 'channels' not in self.__dict__:
                self.channels = {}
            self.channels[alias] = channel
            if autojoin:
                channel.joined_by(self.ref())

    def remove_channel(self, alias):
        me = self.ref()
        channel = self.channels[alias]
        if me in channel._participants:
            channel.left_by(me)
        del me.channels[alias]


def lock_invited(channel, who):
    """
    Lock function invited().
    :type channel: mudslingcore.channels.Channel
    :type who: mudslingcore.channels.ChannelUser
    """
    return channel.isa(Channel) and (who in channel.invitees
                                     or who.has_perm('join any channel'))


def lock_operator(channel, who):
    return channel.isa(Channel) and (who in channel.operators
                                     or who.has_perm('global operator'))
