import time


class Session(object):
    """
    Abstract class meant to be implemented by protocol classes representing a
    single client connection to the game.
    """

    #: @ivar: Time the Session was opened.
    time_connected = 0

    def init_session(self):
        self.time_connected = time.time()

    def receive_input(self, line):
        self.send_output("%s received: %s" % (self, line))

    def send_output(self, line):
        if line.__class__ == list:
            for l in line:
                self.send_output(l)
            return
        self._send_line(line)

    def _send_line(self, line):
        """
        Children should override!
        """
