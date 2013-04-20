import sys

from twisted.python.usage import UsageError
from twisted.internet import reactor

from mudsling.options import Options
from mudsling.core import MUDSling
from mudsling.config import config

if __name__ == '__main__':
    options = Options()
    try:
        options.parseOptions(sys.argv[1:])
    except UsageError as e:
        sys.stderr.write(e.message + '\n' + str(options))
        exit(1)

    game = MUDSling(options['gamedir'], options.configPaths())
    game.setName('main')  # Used by AppRunner to find exit code
    if options['debugger']:
        config.set('Plugins', 'SimpleTelnetServer', 'Enabled')
        config.set('Proxy', 'enabled', 'No')

    game.startService()
    reactor.run()
