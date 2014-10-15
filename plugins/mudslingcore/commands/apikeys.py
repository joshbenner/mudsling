
from mudsling.commands import Command
from mudsling.locks import Lock
from mudsling.parsers import MatchObject, StringListStaticParser
from mudsling.objects import BasePlayer

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
        :type actor: mudslingcore.object.Player
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
        footer = ' {ySee more info with @apikey <id>'
        actor.msg(ui.report('API Keys for %s' % title,
                            self.key_table(actor, keys), footer))

    def key_table(self, actor, keys):
        col = ui.Column
        table = ui.Table([
            col('Owner', align='l', data_key='player',
                cell_formatter=actor.name_for),
            col('ID', align='l', data_key='id'),
            col('Date Issued', align='l', data_key='date_issued',
                cell_formatter=ui.format_timestamp,
                formatter_args=('short',))
        ])
        table.add_rows(*keys)
        return table


class APIKeyCmd(Command):
    """
    @apikey <id>

    Display details on a single API Key.
    """
    aliases = ('@apikey', '@apikey-info', '@show-apikey')
    syntax = '<apikey>'
    arg_parsers = {'apikey': restserver.get_api_key}
    lock = use_api

    def run(self, actor, apikey):
        """
        :type actor: mudslingcore.object.Player
        :type apikey: restserver.APIKey
        """
        if apikey.player == actor or actor.has_perm('administer api'):
            # noinspection PyTypeChecker
            table = ui.keyval_table((
                ('Owner', actor.name_for(apikey.player)),
                ('ID', apikey.id),
                ('Secret', apikey.key),
                ('Date Issued', ui.format_timestamp(apikey.date_issued)),
                ('Valid', '{gYes' if apikey.valid else '{rNo'),
                ('Authorizations', ', '.join(apikey.authorizations))
            ))
            actor.msg(ui.report('API Key Details for %s' % apikey.id, table))
        else:
            raise self._err('Permission denied.')


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
        :type actor: mudslingcore.object.Player
        :type player: BasePlayer
        """
        key = restserver.APIKey(player)
        restserver.register_api_key(key)
        actor.tell('API Key ({y', key.id, '{n) generated for {c',
                   player, '{n.')


class APIKeyInvalidateCmd(Command):
    """
    @apikey-invalidate <id>

    Invalidate an API Key.
    """
    aliases = ('@apikey-invalidate', '@invalidate-apikey')
    syntax = '<apikey>'
    arg_parsers = {'apikey': restserver.get_api_key}
    lock = administer_api

    def run(self, actor, apikey):
        """
        :type actor: mudslingcore.object.Player
        :type apikey: restserver.APIKey
        """
        if apikey.valid:
            apikey.valid = False
            actor.tell('API Key {y', apikey.id, '{n ({c', apikey.player, '{n)',
                       ' has been revoked.')
        else:
            raise self._err('Key is already invalid.')


class APIKeyGrantCmd(Command):
    """
    @apikey-grant <auth>[, <auth>, ...] to <id>

    Grant authorizations (permissions) to the specified API Key.
    """
    aliases = ('@apikey-grant',)
    syntax = '<authorizations> to <apikey>'
    arg_parsers = {
        'authorizations': StringListStaticParser,
        'apikey': restserver.get_api_key
    }
    lock = administer_api

    def run(self, actor, authorizations, apikey):
        grant = []
        for auth in authorizations:
            if not apikey.is_authorized(auth):
                apikey.grant_authorization(auth)
                grant.append(auth)
        actor.tell('Granted authorizations ({m', '{n, {m'.join(grant), '{n)',
                   ' to {c', apikey.player, "{n's API key ({y", apikey.id,
                   '{n).')


class APIKeyRevokeCmd(Command):
    """
    @apikey-revoke <auth>[, <auth>, ...] from <id>

    Revoke authorizations (permissions) from the specified API key.
    """
    aliases = ('@apikey-revoke',)
    syntax = '<authorizations> from <apikey>'
    arg_parsers = {
        'authorizations': StringListStaticParser,
        'apikey': restserver.get_api_key
    }
    lock = administer_api

    def run(self, actor, authorizations, apikey):
        revoke = []
        for auth in authorizations:
            if apikey.is_authorized(auth):
                apikey.revoke_authorization(auth)
                revoke.append(auth)
        actor.tell('Revoked authorizations ({m', '{n, {m'.join(revoke), '{n)',
                   ' from {c', apikey.player, "{n's API key ({y", apikey.id,
                   '{n).')

