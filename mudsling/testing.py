import os

import mudsling
from mudsling.sessions import Session
import mudsling.runner
from mudsling.options import get_options
from mudsling.core import MUDSling
import mudsling.utils.string as str_utils


class TestSession(Session):
    """
    A mock client connection.
    """
    connected = False
    disconnect_reason = None

    def __init__(self, game):
        super(TestSession, self).__init__()
        self.game = game
        self.output = ''
        self.open_session()

    def receive_input(self, line):
        return super(TestSession, self).receive_input(str(line))

    def raw_send_output(self, text):
        self.output += text

    def disconnect(self, reason):
        self.disconnect_reason = reason
        self.connected = False

    def output_contains(self, text, reset=True):
        result = str(text) in self.output
        if reset:
            self.output = ''
        return result


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
    game.startService()
    return game


cleanup_contexts = {}
current_cleanup_context = None


def set_cleanup_context(key):
    global current_cleanup_context
    cleanup_contexts[key] = []
    current_cleanup_context = key


def get_cleanup_context(key):
    return cleanup_contexts[key]


def remove_cleanup_context(key):
    del cleanup_contexts[key]


def add_cleanup(task, key=None):
    key = current_cleanup_context if key is None else key
    if key is not None:
        cleanup_contexts[key].append(task)


class Cleanup(object):
    def do(self):
        raise NotImplementedError()


class CleanupCallback(Cleanup):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def do(self):
        self.func(*self.args, **self.kwargs)


class CleanupObj(Cleanup):
    def __init__(self, *objects):
        self.objects = objects

    def do(self):
        for obj in self.objects:
            obj.delete()


def cleanup(key):
    for task in get_cleanup_context(key):
        task.do()
    remove_cleanup_context(key)