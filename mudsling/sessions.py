import time
import logging
import traceback

from mudsling.ansi import parse_ansi


class Session(object):
    """
    Abstract class meant to be implemented by protocol classes representing a
    single client connection to the game.

    @ivar time_connected: Time the session was opened.
    @ivar player: The player object associated with this session.
    @ivar line_delimiter: How line endings are indicated.
    @ivar game: Reference to game object. Protocol must set this!
    """

    time_connected = 0

    #: @type: mudsling.objects.BasePlayer
    player = None

    line_delimiter = '\r\n'

    #: @type: mudsling.server.MUDSling
    game = None

    ansi = False
    xterm256 = False

    def openSession(self):
        self.time_connected = time.time()
        self.game.session_handler.connectSession(self)
        logging.info("Session %s connected." % self)

    def sessionClosed(self):
        self.game.session_handler.disconnectSession(self)
        if self.player is not None:
            self.player.sessionDetached(self)
        logging.info("Session %s disconnected." % self)

    def receiveInput(self, line):
        line = line.strip()
        if self.player is None:
            self.game.login_screen.processInput(self, line)
        else:
            #noinspection PyBroadException
            try:
                self.player.processInput(line)
            except:
                errmsg = "UNHANDLED EXCEPTION\n%s" % traceback.format_exc()
                logging.error(errmsg)

    def sendOutput(self, text, flags=None):
        """
        Send output to the Session.

        @param text: Text to send. Can be a list.
        @param flags: A dictionary of flags to modify how the text is output.
        @type text: str
        """
        if flags is None:
            flags = {}
        if text.__class__ == list:
            for l in text:
                self.sendOutput(l)
            return
        if not text.endswith(self.line_delimiter):
            text += self.line_delimiter

        if self.ansi and ('raw' not in flags or not flags['raw']):
            text = parse_ansi(text, xterm256=self.xterm256)
        else:
            text = parse_ansi(text, strip_ansi=True)

        self.rawSendOutput(text)

    def rawSendOutput(self, text):
        """
        Children should override!
        """

    def disconnect(self, reason):
        """
        Disconnect this session. Children must implement!
        """

    def attachToPlayer(self, player):
        """
        Attach this session to a player object.

        @param player: The player to attach to.
        @type player: mudsling.objects.BasePlayer
        """
        if self.player is not None:
            self.detach()
        self.player = player
        player.sessionAttached(self)

    def detach(self):
        """
        Detaches the session from the object it's currently connected to.
        """
        if self.player is not None:
            self.player.sessionDetached(self)
            self.player = None


class SessionHandler(object):
    """
    Tracks all sessions connected to the game.

    @ivar sessions: Set of all active sessions.
    @type sessions: set

    @ivar game: Reference to the game
    @type game: mudsling.server.MUDSling
    """

    sessions = set()
    game = None

    def __init__(self, game):
        self.game = game

    def connectSession(self, session):
        """
        Attach a new session to the handler.

        @type session: Session
        """
        self.sessions.add(session)
        self.game.login_screen.sessionConnected(session)

    def disconnectSession(self, session):
        """
        Detatch a session from the handler.

        @type session: Session
        """
        self.sessions.remove(session)
