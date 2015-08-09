import os
import logging
import sys

from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks
from crochet import setup, run_in_reactor, wait_for

import mudsling
from mudsling.sessions import Session
import mudsling.runner
from mudsling.options import get_options
from mudsling.core import MUDSling
import mudsling.utils.string as str_utils
from mudsling.utils.sequence import CaselessDict


def run_behave():
    from behave.__main__ import main
    sys.argv[0] = ''
    sys.exit(main())


def sleep(seconds):
    from twisted.internet import reactor

    @wait_for(timeout=seconds)
    def _sleep(seconds):
        return deferLater(reactor, seconds, lambda: None)

    _sleep(seconds)


class TestSession(Session):
    """
    A mock client connection.
    """
    connected = False
    disconnect_reason = None

    def __init__(self, game, name):
        super(TestSession, self).__init__()
        self.game = game
        self.name = name
        self.output = ''
        self.open_session()

    @run_in_reactor
    def receive_input(self, line):
        return super(TestSession, self).receive_input(str(line))

    def raw_send_output(self, text):
        self.output += text

    def reset_output_buffer(self):
        self.output = ''

    def disconnect(self, reason):
        self.disconnect_reason = reason
        self.connected = False

    def output_contains(self, text, reset=False, wait=0.01):
        if wait is not None:
            sleep(wait)
        result = str(text) in self.output
        if reset:
            self.reset_output_buffer()
        return result


class SessionNameAlreadyUsed(Exception):
    pass


class SessionNameNotFound(Exception):
    pass


#: :type: mudsling.core.MUDSling
_game = None


def set_game(thegame):
    global _game
    _game = thegame


def game():
    """:rtype: mudsling.core.MUDSling"""
    return _game


#: :type: dict of (str, TestSession)
sessions = CaselessDict()


def new_session(name="I"):
    """
    Connect a new test session to a game instance.

    :param name: The name to give the session.
    :type name: str

    :rtype: TestSession
    """
    if name in sessions and sessions[name].connected:
        raise SessionNameAlreadyUsed()
    session = TestSession(game(), name)
    sessions[name] = session
    add_cleanup(CleanupSession(session))
    logging.debug('Added session "%s"' % name)
    return session


def get_session(name):
    """
    Retrieve a session.

    :param name: The name of the session to retrieve.
    :type name: str

    :rtype: TestSession
    """
    try:
        return sessions[name]
    except KeyError:
        return new_session(name)


def remove_session(name):
    """
    Remove a session.

    :param name: The name of the session to remove.
    :type name: str
    """
    if name in sessions:
        del sessions[name]


def bootstrap_game(data_path=None, params=(), settings_text=''):
    """
    Bootstrap a test version of the game.

    :param data_path: The working directory for the test game.
    :type data_path: str

    :param settings_text: An optional string to treat as the settings file.
    :type settings_text: str

    :return: A game instance.
    :rtype: mudsling.core.MUDSling
    """
    logging.debug("Bootstrapping game...")
    if data_path is None:
        data_path = os.path.join(os.getcwd(), '.testruns',
                                 str_utils.random_string(length=8))
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    options = get_options(params)
    gamedir = mudsling.runner.init_game_dir(data_path)
    options['gamedir'] = gamedir
    with open(os.path.join(gamedir, 'settings.cfg'), 'w') as f:
        f.write(settings_text)
    game = MUDSling(options)
    mudsling.game = game
    set_game(game)
    game.startService()
    setup()
    return game


cleanup_contexts = {}
current_cleanup_context = None


def set_cleanup_context(key):
    global current_cleanup_context
    cleanup_contexts[key] = []
    current_cleanup_context = key
    logging.debug('Set cleanup context: %r' % key)


def get_cleanup_context(key):
    return cleanup_contexts[key]


def remove_cleanup_context(key):
    logging.debug('Remove cleanup context %r' % key)
    del cleanup_contexts[key]


class NoCleanupContextSet(Exception):
    pass


def add_cleanup(task, key=None):
    key = current_cleanup_context if key is None else key
    if key is not None:
        logging.debug('Add cleanup %r to context %r' % (task, key))
        cleanup_contexts[key].append(task)
    else:
        raise NoCleanupContextSet()


class Cleanup(object):
    def do(self):
        raise NotImplementedError()


class CleanupCallback(Cleanup):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def do(self):
        logging.debug('Cleanup %r' % self.func)
        self.func(*self.args, **self.kwargs)


class CleanupObj(Cleanup):
    def __init__(self, *objects):
        self.objects = objects

    def do(self):
        for obj in self.objects:
            logging.debug('Cleanup object %s (#%d)' % (obj.name, obj.obj_id))
            obj.delete()


class CleanupSession(Cleanup):
    def __init__(self, session):
        self.session = session

    def do(self):
        logging.debug('Cleanup session "%s"' % self.session.name)
        self.session.disconnect(reason='Cleanup')
        remove_session(self.session.name)


def cleanup(key):
    logging.debug('Cleaning up context %r' % key)
    for task in get_cleanup_context(key):
        task.do()
    remove_cleanup_context(key)


if __name__ == '__main__':
    run_behave()