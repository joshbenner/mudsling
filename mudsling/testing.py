from mudsling.sessions import Session


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

    def raw_send_output(self, text):
        self.output += text

    def disconnect(self, reason):
        self.disconnect_reason = reason
        self.connected = False