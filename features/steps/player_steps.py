import logging

from behave import *

import mudsling.utils.string as str_utils
from mudsling.testing import *
from mudsling.registry import players as player_registry


@given('The player "{name}" exists')
def player_exists(context, name):
    existing = player_registry.find_by_name(name)
    if existing is None:
        player_class = game().player_class
        pword = str_utils.random_string(10)
        #: :type: mudsling.objects.BasePlayer
        player = player_class.create(names=(name,), password=pword,
                                     makeChar=True)
        add_cleanup(CleanupObj(player.default_object, player))
        logging.info("Created player %s (#%d, char: #%d)"
                     % (name, player.obj_id, player.default_object.obj_id))
    else:
        logging.debug('Found existing player %s (#%d)'
                      % (existing.name, existing.obj_id))
        player = existing
    context.objects['player %s' % name] = player
    context.objects[name] = player.default_object


@given('The player "{name}" exists with password "{password}"')
def player_exists_with_password(context, name, password):
    player_exists(context, name)
    #: :type: mudsling.objects.BasePlayer
    player = context.objects['player %s' % name]
    password = str(password)
    player.set_password(password)
    logging.info("Set password for player %s (#%d) to '%s'"
                 % (player.name, player.obj_id, password))


@given("{name} is connected")
@given('"{name}" is connected')
def player_is_connected(context, name):
    player_exists(context, name)
    player = context.objects['player %s' % name]
    session = get_session(name)
    session.attach_to_player(player)
    logging.debug('Attached session "%s" to player %s (#%d)'
                  % (name, player.name, player.obj_id))


@given("{name1} and {name2} are connected")
def two_players_are_connected(context, name1, name2):
    player_is_connected(context, name1)
    player_is_connected(context, name2)