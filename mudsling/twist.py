"""
Custom Twisted Matrix handling.
"""


def run_app(filepath, extra=None):
    from sys import argv
    from twisted.application import app

    from twisted.python.runtime import platformType
    if platformType == "win32":
        from twisted.scripts._twistw import ServerOptions,\
            WindowsApplicationRunner as _SomeApplicationRunner
    else:
        from twisted.scripts._twistd_unix import ServerOptions,\
            UnixApplicationRunner as _SomeApplicationRunner

    class AppRunner(_SomeApplicationRunner):
        def run(self, extra=None):
            self.preApplication()
            self.application = self.createOrGetApplication()
            self.application._extra = extra

            self.logger.start(self.application)

            self.postApplication()
            self.logger.stop()

    def runApp(config):
        AppRunner(config).run(extra)

    argv[1:] = [
        '-y', filepath
    ]
    app.run(runApp, ServerOptions)
