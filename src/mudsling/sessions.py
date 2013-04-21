import time
import logging
import traceback
import re

import zope.interface
from twisted.internet import defer

from mudsling.config import config
from mudsling.utils import string


# Do not allow players to use control codes. Would be difficult, but not
# impossible, for a malicious user to send other players control sequences.
from mudsling.utils.string import mxp

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
    last_activity = 0
    ip = ''
    hostname = ''

    #: @type: mudsling.objects.BasePlayer
    player = None

    line_delimiter = '\r\n'

    input_processor = None
    profile = False

    #: @type: mudsling.server.MUDSling
    game = None

    ansi = False
    xterm256 = False
    mxp = False
    idle_cmd = 'IDLE'

    def set_option(self, name, value):
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
                self.send_output('MXP Enabled',
                                {"mxpmode": mxp.LINE_MODES.LOCK_SECURE})

    def open_session(self, resync=False):
        self.time_connected = time.time()
        self.idle_cmd = config.get('Main', 'idle command')
        self.game.session_handler.connect_session(self, resync=resync)
        logging.info("Session %s connected." % self)

    def session_closed(self):
        self.game.session_handler.disconnect_session(self)
        if self.player is not None:
            self.player.session_detached(self)
        logging.info("Session %s disconnected." % self)

    def redirect_input(self, where):
        if IInputProcessor.providedBy(self.input_processor):
            self.input_processor.lost_input_capture(self)
        self.input_processor = where
        if IInputProcessor.providedBy(where):
            where.gained_input_capture(self)

    def reset_input_capture(self):
        self.redirect_input(self.player)

    def receive_input(self, line):
        if line == self.idle_cmd:
            return
        start = time.clock()
        self.last_activity = time.time()
        line = line.strip()
        if self.input_processor is None:
            self.game.login_screen.process_input(self, line)
        else:
            #noinspection PyBroadException
            try:
                self.input_processor.process_input(line)
            except SystemExit:
                raise
            except:
                errmsg = "UNHANDLED EXCEPTION\n%s" % traceback.format_exc()
                logging.error(errmsg)
        if self.profile:
            duration = (time.clock() - start) * 1000
            self.send_output("Command time: %.3fms" % duration)

    def send_output(self, text, flags=None):
        """
        Send output to the Session.

        @param text: Text to send. Can be a list.
        @param flags: A dictionary of flags to modify how the text is output.
        @type text: str

        @rtype: L{twisted.internet.defer.Deferred}
        """
        if flags is None:
            flags = {}
        if isinstance(text, list):
            for l in text:
                self.send_output(l)
            return
        text = str(text)
        if not text.endswith(self.line_delimiter):
            text += self.line_delimiter

        raw = flags.get('raw', False)

        if self.mxp:
            if raw:
                # Locked mode parses no MXP at all.
                text = mxp.line_mode(text, mxp.LINE_MODES.LOCKED)
            else:
                mxpMode = flags.get('mxpmode', None)
                text = mxp.prepare(text)
                if mxpMode is not None:
                    text = mxp.line_mode(text, mxpMode)
        else:
            text = mxp.strip(text)

        if self.ansi and not raw:
            text = text.replace('\n', string.ansi.ANSI_NORMAL + '\n')
            text = (string.parse_ansi(text, xterm256=self.xterm256)
                    + string.ansi.ANSI_NORMAL)
        elif not raw:
            text = string.parse_ansi(text, strip_ansi=True)

        return self.raw_send_output(text)

    def raw_send_output(self, text):
        """
        Children should override!

        @rtype: L{twisted.internet.defer.Deferred}
        """

    def disconnect(self, reason):
        """
        Disconnect this session. Children must implement!
        """

    def attach_to_player(self, player):
        """
        Attach this session to a player object.

        @param player: The player to attach to.
        @type player: mudsling.objects.BasePlayer
        """
        if self.player is not None:
            self.detach()
        self.player = player._real_object()
        self.input_processor = self.player
        player.session_attached(self)

    def detach(self):
        """
        Detaches the session from the object it's currently connected to.
        """
        if self.player is not None:
            self.player.session_detached(self)
            self.input_processor = None
            self.player = None

    def connected_seconds(self):
        return time.time() - self.time_connected

    def idle_seconds(self):
        return time.time() - self.last_activity


class SessionHandler(object):
    """
    Tracks all sessions connected to the game.

    @ivar sessions: Set of all active sessions.
    @type sessions: set

    @ivar game: Reference to the game
    @type game: mudsling.core.MUDSling
    """
    sessions = None
    game = None

    def __init__(self, game):
        self.game = game
        self.sessions = set()

    def connect_session(self, session, resync=False):
        """
        Attach a new session to the handler.

        @type session: Session
        """
        self.sessions.add(session)
        if not resync:
            self.game.login_screen.session_connected(session)

    def disconnect_session(self, session):
        """
        Detatch a session from the handler. Do not call this to disconnect a
        session. Instead, call session.disconnect(), which will in turn call
        this.

        @type session: Session
        """
        self.sessions.remove(session)

    def disconnect_all_sessions(self, reason):
        """
        Disconnects all sessions.
        """
        for session in list(self.sessions):
            session.disconnect(reason)

    def output_to_all_sessions(self, text, flags=None):
        """
        @rtype: L{twisted.internet.defer.DeferredList}
        """
        calls = [s.send_output(text, flags=flags) for s in self.sessions]
        return defer.DeferredList(calls)


class IInputProcessor(zope.interface.Interface):
    """
    Receives input from sessions. Holds responsibility for parsing input and
    dispatching resulting commands.
    """

    def process_input(raw, session=None):
        """
        Handle the raw input. Return value not used.
        """

    def gained_input_capture(session):
        """
        Called when this IInputProcessor will now receive input from a session.
        """

    def lost_input_capture(session):
        """
        Called when this IInputProcess will no longer receive input from the
        specified session.
        """
