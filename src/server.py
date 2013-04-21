import sys
import os
import logging

from twisted.internet import reactor

from mudsling.options import get_options
from mudsling.core import MUDSling
from mudsling.config import config
from mudsling.logs import open_log
from mudsling.pid import check_pid


def run_server(args=None):
    # Startup.
    options = get_options(args)
    log_level = logging.DEBUG if options['debugger'] else logging.INFO
    open_log(filepath=os.path.join(options['gamedir'], 'server.log'),
             level=log_level,
             stdout=bool(options['debugger']))
    pidfile = os.path.join(options['gamedir'], 'server.pid')
    check_pid(pidfile, kill=True)

    # Run game.
    game = MUDSling(options['gamedir'], options.configPaths())
    if options['debugger']:
        config.set('Plugins', 'SimpleTelnetServer', 'Enabled')
        config.set('Proxy', 'enabled', 'No')
    game.startService()
    reactor.run()

    # Shutdown.
    os.remove(pidfile)
    sys.exit(game.exit_code)

if __name__ == '__main__':
    run_server()
