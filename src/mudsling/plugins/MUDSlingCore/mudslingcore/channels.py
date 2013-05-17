"""
MUDSlingCore channel system.
"""
import logging
import re

import zope.interface

from mudsling.objects import NamedObject
from mudsling import locks
from mudsling.commands import Command, IHasCommands
from mudsling.parsers import BoolStaticParser, MatchDescendants
from mudsling import errors

from mudslingcore.ui import ClassicUI

ui = ClassicUI()


class Channel(NamedObject):
    """
    Channel object stores the state/config for a channel in the game, the list
    of participants, and processes/routes messages to/from those participants.

    @ivar operators: Players who can administer the channel.
    @ivar _participants: Players who are joined to the channel.
    @ivar invitees: Players who have been invited to the (restricted) channel.
    @ivar voice: If None, all can speak. Otherwise, set of participants that
        can speak on the channel.
    @type voice: C{None} or C{set}
    """
    operators = set()
    _participants = set()
    invitees = set()
    voice = None
    locks = locks.LockSet('join:all')

    def __init__(self, **kwargs):
        super(Channel, self).__init__(**kwargs)
        self.operators = set()
        self._participants = set()
        self.invitees = set()

    @property
    def prefix(self):
        return ''.join(['[', self.name, ']'])

    @property
    def participants(self):
        return [p for p in self._participants
                if self.db.is_valid(p, cls=ChannelUser) and p.connected]

    def _prepare_message(self, msg):
        if isinstance(msg, tuple):
            msg = list(msg)
        elif isinstance(msg, basestring):
            msg = [msg]
        prefix = self.prefix
        out = []
        for line in msg:
            out.append(prefix + line)
        return out

    def broadcast(self, msg, who=None):
        msg = self._prepare_message(msg)
        for p in self.participants:
            try:
                p.msg(msg)
            except Exception:
                logging.warning("Bad object on chan %s: %r" % (self.name, p))

    def add_operator(self, who):
        self.operators.add(who)

    def joinable_by(self, who):
        return self.allows(who, 'join') or who in self.operators

    def speakable_by(self, who):
        if who in self.participants:
            if self.voice is None or who in self.voice:
                return True
        if who in self.operators:
            return True
        return False

    def joined_by(self, who):
        self._participants.add(who.ref())
        self.broadcast(who.channel_name + ' has joined ' + self.name + '.')

    def left_by(self, who):
        self.broadcast(who.channel_name + ' has left ' + self.name + '.')


class ChannelsCmd(Command):
    """
    +channels[/all]

    Show a list of channels. The all switch shows all channels accessible to
    the player, while the default is to just show channels the player has
    added to their list of aliases.
    """
    aliases = ('+channels',)
    switch_parsers = {
        'all': BoolStaticParser,
    }
    switch_defaults = {
        'all': False,
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.channels.ChannelUser}
        @type actor: L{mudslingcore.channels.ChannelUser}
        @type args: C{dict}
        """
        if self.switches['all']:
            my_channels = actor.channels.values()
            channels = actor.channels.items()
            for channel in self.game.db.descendants(Channel):
                if channel not in my_channels:
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
                '{gYes' if actor in channel._participants else '{rNo'
            ])

        table = ui.Table([
            ui.Column('Alias'),
            ui.Column('Channel', align='l'),
            ui.Column('#', align='r'),
            ui.Column('Joined')
        ])
        table.add_rows(*rows)
        actor.msg(ui.report('Channels', table))


class ChanCreateCmd(Command):
    """
    +chancreate <channel>

    Create a new channel.
    """
    aliases = ('+chancreate', '+createchan', '+mkchan')
    syntax = '<channel>'
    lock = 'perm(create channels)'

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.channels.ChannelUser}
        @type actor: L{mudslingcore.channels.ChannelUser}
        @type args: C{dict}
        """
        existing = self.game.db.match_descendants(args['channel'], Channel,
                                                  exactOnly=True)
        if existing:
            actor.msg('{yChannel `{c%s{y` already exists.' % existing[0].name)
        else:
            #: @type: Channel
            channel = Channel.create(names=(args['channel'],))
            channel.add_operator(actor)
            actor.msg('{gChannel created: {c%s' % channel.name)


class ChanAddCmd(Command):
    """
    +chanadd <channel>=<alias>

    Adds a channel to your personal channel aliases.
    """
    aliases = ('+chanadd', '+addchan')
    syntax = '<channel> {=} <alias>'
    arg_parsers = {
        'channel': MatchDescendants(cls=Channel, search_for='channel',
                                    show=True)
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.channels.ChannelUser}
        @type actor: L{mudslingcore.channels.ChannelUser}
        @type args: C{dict}
        """
        try:
            actor.add_channel(args['channel'], args['alias'])
        except (ValueError, errors.AccessDenied) as e:
            actor.msg('{y' + e.message)


class ChanRemoveCmd(Command):
    """
    +chanremove <alias>

    Removes a channel from your personal aliases.
    """
    aliases = ('+chanremove', '+chanrem', '+remchan', '+rmchan')
    syntax = '<alias>'
    lock = locks.all_pass


class ChannelUser(NamedObject):
    zope.interface.implements(IHasCommands)

    private_commands = [
        ChannelsCmd,
        ChanCreateCmd,
        ChanAddCmd,
        ChanRemoveCmd,
    ]

    def __init__(self, **kwargs):
        super(ChannelUser, self).__init__(**kwargs)
        self.channels = {}

    @property
    def channel_name(self):
        return self.name

    def msg(self, text):
        # Placeholder.
        pass

    def channel_alias(self, channel):
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
            self.channels[alias] = channel
            if autojoin:
                channel.joined_by(self.ref())
