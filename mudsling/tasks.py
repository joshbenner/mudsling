"""
MUDSling Task system.
"""
import logging
import traceback

from twisted.internet.task import LoopingCall
from twisted.internet.defer import CancelledError

from mudsling.storage import Persistent


class BaseTask(Persistent):
    """
    Base task class. Handles the interaction with the Database for persistance.

    @cvar db: A class-level reference to the database.

    @ivar id: Arbitrary numeric ID to identify task instance.
    @ivar alive: If True, then the task has not been killed. Set by database
        upon task registration.
    """

    # Avoid saving (probably mistaken) db reference.
    _transientVars = ['db']

    #: @type: mudsling.storage.Database
    db = None

    #: @type: int
    id = None
    alive = False

    def __init__(self):
        self.db.registerTask(self)

    def kill(self):
        """
        Kill this task. Children should take care to implement this according
        to their task mechanism!
        """
        self.alive = False
        self.db.removeTask(self.id)

    def onServerStartup(self):
        """
        Called on all registered tasks upon server startup.
        """

    def onServerShutdown(self):
        """
        Called on all registered tasks upon server shutdown.
        """


class IntervalTask(BaseTask):
    """
    IntervalTask executes a callback at an interval.
    """

    _transientVars = ['_looper']

    _callback = None
    _interval = None
    _immediate = False
    _iterations = None
    _args = []
    _kwargs = {}

    #: @type: LoopingCall
    _looper = None

    run_count = 0

    def __init__(self, callback, interval, immediate=False, iterations=None,
                 args=None, kwargs=None):
        """
        @param callback: The callable to call at intervals.

        @param interval: The interval at which to execute the callback.
        @type interval: int or float

        @param immediate: If True, then the first iteration fires immediately.
        @type immediate: bool

        @param iterations: The maximum number of iterations this task should
            run. If None, then there is no limit.
        @type iterations: int
        """
        super(IntervalTask, self).__init__()
        self._callback = callback
        self._interval = interval
        self._immediate = immediate
        self._iterations = iterations
        if args is not None:
            self._args = args
        if kwargs is not None:
            self._kwargs = kwargs
        self.schedule()

    def schedule(self):
        self._looper = LoopingCall(self._run)
        d = self._looper.start(self._interval, now=self._immediate)
        d.addErrback(self._errBack)

    def kill(self):
        if self._looper is not None and self._looper.running:
            self._looper.stop()
        super(IntervalTask, self).kill()

    def _run(self):
        self.run_count += 1
        #noinspection PyBroadException
        try:
            self._callback(*self._args, **self._kwargs)
        except:
            logging.error("Error in %s:\n%s" % (self, traceback.format_exc()))
        if self._iterations is not None and self.run_count >= self._iterations:
            self.kill()

    def _errBack(self, error):
        """
        @type error: twisted.python.failure.Failure
        """
        error.trap(Exception)
        if error.type == CancelledError:
            return
        tb = ''.join(traceback.format_exception(error.type, error.value,
                                                error.getTraceback()))
        logging.error("Error in %s:\n%s" % (self, tb))

    def onServerStartup(self):
        if not self.alive:
            return
        self.schedule()
        super(IntervalTask, self).onServerStartup()

    def onServerShutdown(self):
        if self._looper is not None and self._looper.running:
            self._looper.stop()
        super(IntervalTask, self).onServerShutdown()
