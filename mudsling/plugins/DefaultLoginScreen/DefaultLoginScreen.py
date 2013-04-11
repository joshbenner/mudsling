import os
import re
from collections import namedtuple

from mudsling.extensibility import LoginScreenPlugin
from mudsling.match import match_objlist
from mudsling.utils.password import Password
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
            r'q(?:uit)?$',
            'quit',
            'Disconnect.',
            'doQuit'
        )
    )

    def activate(self):
        super(DefaultLoginScreen, self).activate()
        plugin_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(plugin_path, 'login_screen.txt')
        with open(file_path, 'rU') as f:
            self.screen = [line.rstrip('\n') for line in f.readlines()]

    def sessionConnected(self, session):
        self.doLook(session)

    def processInput(self, session, input):
        for cmd in self.commands:
            m = re.match(cmd.pattern, input, re.IGNORECASE)
            if m:
                getattr(self, cmd.func)(session, input, args=m.groups())
                return
        session.sendOutput("{rInvalid Command.")
        self.doHelp(session)

    def doLook(self, session, input=None, args=None):
        session.sendOutput(self.screen)
        self.doHelp(session, input, args)

    def doHelp(self, session, input=None, args=None):
        #: @type: mudsling.sessions.Session
        s = session
        s.sendOutput("Available Commands:")
        width = max(*[len(cmd.syntax) for cmd in self.commands])
        format = "  {cmd.syntax:%d} : {cmd.desc}" % width
        for cmd in self.commands:
            #noinspection PyTypeChecker
            s.sendOutput(format.format(cmd=cmd))

    def doQuit(self, session, input=None, args=None):
        session.disconnect("quit")

    def doConnect(self, session, input=None, args=None):
        errmsg = "Unknown player name or password."
        username, password = args

        matches = match_objlist(username,
                                self.game.db.descendants(BasePlayer),
                                exactOnly=True)

        if len(matches) > 1:
            # This hopefully won't happen...
            session.sendOutput(errmsg)
            return
        elif len(matches) == 0:
            session.sendOutput(errmsg)
            return

        #: @type: BasePlayer
        player = matches[0]
        if (isinstance(player.password, Password)
                and player.password.matchesPassword(password)):
            session.attachToPlayer(player)
        else:
            session.sendOutput(errmsg)
