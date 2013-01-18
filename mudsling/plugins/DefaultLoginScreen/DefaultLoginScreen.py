import os

from mudsling.plugins import LoginScreenPlugin


class DefaultLoginScreen(LoginScreenPlugin):

    login_screen = ""

    def activate(self):
        super(DefaultLoginScreen, self).activate()
        plugin_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(plugin_path, 'login_screen.txt')
        with open(file_path, 'rU') as f:
            self.login_screen = [line.rstrip('\n') for line in f.readlines()]

    def sessionConnected(self, session):
        session.sendOutput(self.login_screen)

    def processInput(self, session, input):
        session.sendOutput("%s received: %s" % (self, input))
