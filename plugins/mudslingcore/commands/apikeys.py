
from mudsling.commands import Command
from mudsling.locks import Lock
from mudsling.parsers import MatchObject
from mudsling.objects import BasePlayer
from mudsling.utils.time import datetime_format

import restserver

from mudslingcore.ui import ClassicUI

ui = ClassicUI()

use_api = Lock('has_perm(use api)')
administer_api = Lock('has_perm(administer api)')

match_player = MatchObject(cls=BasePlayer, search_for='player', show=True,
                           context=False)


class APIKeysCmd(Command):
    """
    @apikeys[/all] [<player>]

    Show API keys for specified player (default: self), or across all players
    with /all switch.
    """
    aliases = ('@apikeys', '@apikeys-list')
    syntax = '[<player>]'
    arg_parsers = {'player': match_player}
    lock = use_api
    switch_defaults = {'all': False}

    def run(self, actor, player, switches):
        """
        :type actor: BasePlayer
        :type player: BasePlayer
        :type switches: dict
        """
        all = switches['all']
        if all and player is not None:
            raise self._err('Cannot list all keys AND limit to single player.')
        if all:
            keys = restserver.apikeys.values()
            title = 'All Players'
        else:
            if player is None:
                player = actor
            keys = restserver.get_player_api_keys(player)
            title = actor.name_for(player)
        actor.msg(ui.report('API Keys for %s' % title,
                            self.key_table(actor, keys)))

    def key_table(self, actor, keys):
        secret = lambda k: '{r--REVOKED--' if not k.valid else k.key
        col = ui.Column
        table = ui.Table([
            col('Owner', align='l', data_key='player',
                cell_formatter=actor.name_for),
            col('ID', align='l', data_key='id'),
            col('Secret', align='l', cell_formatter=secret),
            col('Date Issued', align='l', data_key='date_issued',
                cell_formatter=ui.format_timestamp,
                formatter_args=('short',))
        ])
        table.add_rows(*keys)
        return table


class APIKeyAddCmd(Command):
    """
    @apikey-add <player>

    Adds a new API key to the specified player.
    """
    aliases = ('@apikey-add', '@add-apikey')
    syntax = '<player>'
    arg_parsers = {'player': match_player}
    lock = administer_api

    def run(self, actor, player):
        """
        :type actor: BasePlayer
        :type player: BasePlayer
        """
        key = restserver.APIKey(player)
        restserver.register_api_key(key)
        actor.tell('API Key ({y', key.id, '{n) generated for {c',
                   player, '{n.')
