import re
import logging
from collections import namedtuple

from mudsling.extensibility import LoginScreenPlugin
from mudsling.match import match_objlist
from mudsling.objects import BasePlayer


LoginCmd = namedtuple('LoginCmd', 'pattern syntax desc func')


class DefaultLoginScreen(LoginScreenPlugin):

    screen = ""

    commands = (
        LoginCmd(
            pattern=r'l(?:ook)?$',
            syntax='look',
            desc='Display the connection screen.',
            func='doLook'
        ),
        LoginCmd(
            r'(?:(?:h(?:elp)?)|\?)$',
            'help',
            'Display available commands.',
            'doHelp'
        ),
        LoginCmd(
            r'c(?:onn(?:ect)?)? +(?P<name>[^ ]+) +(?P<pass>.+)$',
            'connect <name> <password>',
            'Connect to the game.',
            'doConnect'
        ),
        LoginCmd(
            r'reg(?:ister)? +(?P<name>[^ ]+) +(?P<pass>.+)$',
            'register <name> <password>',
            'Create a new account.',
            'doRegister'
        ),
        LoginCmd(
            r'q(?:uit)?$',
            'quit',
            'Disconnect.',
            'doQuit'
        )
    )

    def __init__(self, *args, **kwargs):
        super(DefaultLoginScreen, self).__init__(*args, **kwargs)
        file_path = self.resource_path('login_screen.txt')
        with open(file_path, 'rU') as f:
            self.screen = [line.rstrip('\n') for line in f.readlines()]

    def session_connected(self, session):
        self.doLook(session)

    def process_input(self, session, input):
        for cmd in self.commands:
            m = re.match(cmd.pattern, input, re.IGNORECASE)
            if m:
                getattr(self, cmd.func)(session, input, args=m.groups())
                return
        session.send_output("{rInvalid Command.")
        self.doHelp(session)

    def doLook(self, session, input=None, args=None):
        session.send_output(self.screen)
        self.doHelp(session, input, args)

    def doHelp(self, session, input=None, args=None):
        #: @type: mudsling.sessions.Session
        s = session
        s.send_output("Available Commands:")
        width = max(*[len(cmd.syntax) for cmd in self.commands])
        format = "  {cmd.syntax:%d} : {cmd.desc}" % width
        for cmd in self.commands:
            #noinspection PyTypeChecker
            s.send_output(format.format(cmd=cmd))

    def doQuit(self, session, input=None, args=None):
        session.disconnect("quit")

    def doConnect(self, session, input=None, args=None):
        errmsg = "Unknown player name or password."
        username, password = args

        matches = match_objlist(username,
                                self.game.db.descendants(BasePlayer),
                                exact=True)

        if len(matches) > 1:
            # This hopefully won't happen...
            session.send_output(errmsg)
            return
        elif len(matches) == 0:
            session.send_output(errmsg)
            return

        #: @type: BasePlayer
        player = matches[0]
        try:
            auth = player.authenticate(password, session)
        except TypeError:
            auth = False
            logging.exception("Auth failed.")
        except Exception:
            logging.exception("Login failed")
            session.send_output("Error logging in!")
            return
        if auth:
            session.attach_to_player(player)
        else:
            session.send_output(errmsg)

    def doRegister(self, session, input=None, args=None):
        if not self.options.getboolean('registration'):
            session.send_output("Registration is currently disabled.")
            return

        username, password = args
        names = [n.strip() for n in username.split(',')]
        playerClass = self.game.player_class

        try:
            player = playerClass.create(names=names,
                                        password=password,
                                        makeChar=True)
        except Exception as e:
            session.send_output(e.message)
            logging.exception("Failed to complete registration")
        else:
            session.send_output("Account '%s' has been created!" % player.name)
            self.doConnect(session, args=(player.name, password))
