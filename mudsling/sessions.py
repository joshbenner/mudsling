import time
import logging
import traceback
import re

from mudsling.utils import string
from mudsling import mxp


# Do not allow players to use control codes. Would be difficult, but not
# impossible, for a malicious user to send other players control sequences.
ILLEGAL_INPUT = re.compile('[' + mxp.GT + mxp.LT + mxp.AMP + chr(27) + ']')


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

    input_processor = None

    #: @type: mudsling.server.MUDSling
    game = None

    ansi = False
    xterm256 = False
    mxp = False

    def setOption(self, name, value):
        """
        Map options and their values onto session attributes. This is used by
        session protocols that do not need to understand types.
        """
        if name == 'mxp':
            before = self.mxp
            self.mxp = bool(value)
            if not before and self.mxp:
                # Make secure mode the default, since we do not allow other
                # players to send MXP sequences.
                self.sendOutput('MXP Enabled',
                                {"mxpmode": mxp.LINE_MODES.LOCK_SECURE})

    def openSession(self, resync=False):
        self.time_connected = time.time()
        self.game.session_handler.connectSession(self, resync=resync)
        logging.info("Session %s connected." % self)

    def sessionClosed(self):
        self.game.session_handler.disconnectSession(self)
        if self.player is not None:
            self.player.sessionDetached(self)
        logging.info("Session %s disconnected." % self)

    def redirectInput(self, where):
        if isinstance(self.input_processor, InputProcessor):
            self.input_processor.lostInputCapture(self)
        self.input_processor = where
        if isinstance(where, InputProcessor):
            where.gainedInputCapture(self)

    def resetInputCapture(self):
        self.redirectInput(self.player)

    def receiveInput(self, line):
        line = line.strip()
        if self.input_processor is None:
            self.game.login_screen.processInput(self, line)
        else:
            #noinspection PyBroadException
            try:
                self.input_processor.processInput(line)
            except SystemExit:
                raise
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
        if isinstance(text, list):
            for l in text:
                self.sendOutput(l)
            return
        text = str(text)
        if not text.endswith(self.line_delimiter):
            text += self.line_delimiter

        raw = flags.get('raw', False)

        if self.mxp:
            if raw:
                # Locked mode parses no MXP at all.
                text = mxp.lineMode(text, mxp.LINE_MODES.LOCKED)
            else:
                mxpMode = flags.get('mxpmode', None)
                text = mxp.prepare(text)
                if mxpMode is not None:
                    text = mxp.lineMode(text, mxpMode)
        else:
            text = mxp.strip(text)

        if self.ansi and not raw:
            text = text.replace('\n', string.ansi.ANSI_NORMAL + '\n')
            text = (string.parse_ansi(text, xterm256=self.xterm256)
                    + string.ansi.ANSI_NORMAL)
        elif not raw:
            text = string.parse_ansi(text, strip_ansi=True)

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
        self.player = player._realObject()
        self.input_processor = self.player
        player.sessionAttached(self)

    def detach(self):
        """
        Detaches the session from the object it's currently connected to.
        """
        if self.player is not None:
            self.player.sessionDetached(self)
            self.input_processor = None
            self.player = None


class SessionHandler(object):
    """
    Tracks all sessions connected to the game.

    @ivar sessions: Set of all active sessions.
    @type sessions: set

    @ivar game: Reference to the game
    @type game: mudsling.core.MUDSling
    """

    sessions = set()
    game = None

    def __init__(self, game):
        self.game = game

    def connectSession(self, session, resync=False):
        """
        Attach a new session to the handler.

        @type session: Session
        """
        self.sessions.add(session)
        if not resync:
            self.game.login_screen.sessionConnected(session)

    def disconnectSession(self, session):
        """
        Detatch a session from the handler. Do not call this to disconnect a
        session. Instead, call session.disconnect(), which will in turn call
        this.

        @type session: Session
        """
        self.sessions.remove(session)

    def disconnectAllSessions(self, reason):
        """
        Disconnects all sessions.
        """
        for session in list(self.sessions):
            session.disconnect(reason)

    def outputToAllSessions(self, text, flags=None):
        for session in self.sessions:
            session.sendOutput(text, flags=flags)


class InputProcessor(object):
    """
    Subclass InputProcessor when you wish your object able to receive raw input
    from a connected session.
    """
    def processInput(self, raw):
        pass

    def gainedInputCapture(self, session):
        pass

    def lostInputCapture(self, session):
        pass
