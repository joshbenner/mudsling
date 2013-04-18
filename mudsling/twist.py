"""
Custom Twisted handling.

Much of this is to extend Twisted just enough to get exit codes working well
with the plugin approach to twisted services and twistd script -- though even
then, only when using our custom twistd entry points.
"""

import sys
from sys import argv

from twisted.application import app
from twisted.application.service import IService
from twisted.python.runtime import platformType

if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions,\
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions,\
        UnixApplicationRunner as _SomeApplicationRunner


class AppRunner(_SomeApplicationRunner):
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
    argv.insert(1, plugin)
    app.run(__run_app, ServerOptions)
