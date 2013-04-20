import sys

from twisted.application import app
from twisted.application.service import IService
from twisted.python.runtime import platformType

if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner as _SomeApplicationRunner

from mudsling.options import Options


class AppRunner(_SomeApplicationRunner):
    def __init__(self, config):
        options = Options()
        options.parseOptions(sys.argv[2:])
        appname = sys.argv[1].rsplit('-', 1)[1]
        config['logfile'] = '%s/%s.log' % (options['gamedir'], appname)
        config['pidfile'] = '%s/%s.pid' % (options['gamedir'], appname)
        if options['debugger']:
            config['nodaemon'] = True
        super(AppRunner, self).__init__(config)

    def startReactor(self, reactor, oldstdout, oldstderr):
        super(AppRunner, self).startReactor(reactor, oldstdout, oldstderr)

        # At this point, the app is exiting. Look for an exit code to use.
        services = self.application.getComponent(IService)
        try:
            main = services.getServiceNamed('main')
            code = main.exit_code
        except (KeyError, AttributeError):
            return
        sys.exit(code)


def run_app(plugin):
    def __run_app(config):
        AppRunner(config).run()

    sys.argv.insert(1, plugin)
    app.run(__run_app, ServerOptions)
