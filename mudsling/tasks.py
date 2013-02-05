"""
MUDSling Task system.
"""
import logging
import traceback
import time

from twisted.internet.task import LoopingCall
from twisted.internet.defer import CancelledError

from mudsling.storage import Persistent


class BaseTask(Persistent):
    """
    Base task class. Handles the interaction with the Database for persistance.
    This is the basic API a task class needs to implement in order to interact
    with the game.

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

    def serverStartup(self):
        """
        Called on all registered tasks upon server startup.
        """

    def serverShutdown(self):
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
    last_run_time = None
    paused = False
    _elapsed_at_pause = None
    _paused_at_shutdown = False

    def __init__(self, callback, interval, immediate=False, iterations=None,
                 args=None, kwargs=None):
        """
        @param callback: The callable to call at intervals.

        @param interval: The interval at which to execute the callback.
        @type interval: int or float or None

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
        self._schedule()

    def _schedule(self, interval=None):
        interval = interval if interval is not None else self._interval
        if interval is not None:  # None interval means it does not schedule.
            now = self._immediate and not self.run_count
            self._looper = LoopingCall(self._run)
            self.last_run_time = time.time()
            d = self._looper.start(interval, now=now)
            d.addErrback(self._errBack)

    def kill(self):
        self._killLooper()
        super(IntervalTask, self).kill()

    def _killLooper(self):
        if self._looper is not None and self._looper.running:
            self._looper.stop()

    def pause(self):
        if not self.paused:
            self._elapsed_at_pause = time.time() - self.last_run_time
            self.paused = True
            self._killLooper()
            return True
        else:
            return False

    def unpause(self):
        if self.paused:
            self.paused = False
            self._schedule(self._interval - self._elapsed_at_pause)

    def _run(self):
        self.run_count += 1
        #noinspection PyBroadException
        try:
            self._callback(*self._args, **self._kwargs)
        except:
            logging.error("Error in %s:\n%s" % (self, traceback.format_exc()))
        if self._iterations is not None and self.run_count >= self._iterations:
            self.kill()
        if self._elapsed_at_pause:
            del self._elapsed_at_pause
            self._killLooper()
            self._schedule()

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

    def serverStartup(self):
        if not self.alive:
            return
        if not self._paused_at_shutdown:
            self.unpause()
            del self._paused_at_shutdown
        super(IntervalTask, self).serverStartup()

    def serverShutdown(self):
        self._paused_at_shutdown = self.paused
        self.pause()
        super(IntervalTask, self).serverShutdown()


class DelayedTask(IntervalTask):
    """
    Run a callback once, after a specified delay. This is mostly a convenience
    and is (literally) equivalent to IntervalTask(iterations=1).
    """
    def __init__(self, callback, delay, *args, **kwargs):
        super(DelayedTask, self).__init__(callback, delay, iterations=1,
                                          args=args, kwargs=kwargs)


class Task(IntervalTask):
    """
    This class is meant to be inherited from as a base for user-defined tasks
    or scripts.
    """
    def __init__(self):
        super(Task, self).__init__(self.run, None)

    def start(self, interval, iterations=None):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def run(self):
        """
        This function is called when the task needs to run an iteration. This
        is generally called every <interval> seconds.
        """

    def onStart(self):
        pass

    def onStop(self):
        pass

    def onPause(self):
        pass

    def onUnpause(self):
        pass

    def onServerStartup(self):
        pass

    def onServerShutdown(self):
        pass
