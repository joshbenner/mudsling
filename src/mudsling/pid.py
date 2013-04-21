import os
import sys
import signal
import errno
import logging

import psutil


def check_pid(pidfile, kill=False):
    """
    Juggle PID file in a cross-platform manner.

    If `pidfile` does not exist, create it. If it does exist, check if the
    process it points to is active. If so, kill the existing process (if the
    `kill` parameter is True), else abort this process.
    """
    if os.path.exists(pidfile):
        try:
            pid = int(open(pidfile).read())
        except ValueError:
            sys.exit("Invalid PID in %s" % pidfile)
        if psutil.pid_exists(pid):
            if kill:
                try:
                    os.kill(pid, signal.SIG_DFL)
                except OSError, why:
                    if why[0] == errno.ESRCH:
                        logging.warning("Removing stale pidfile %s" % pidfile)
                        os.remove(pidfile)
                    else:
                        sys.exit("Error killing old PID %s" % pid)
            else:
                sys.exit("Existing process %s found in %s" % (pid, pidfile))
        # else will be overwritten
    f = open(pidfile, 'wb')
    f.write(str(os.getpid()))
    f.close()
