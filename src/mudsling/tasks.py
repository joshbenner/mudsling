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
    _transient_vars = ['db']

    #: @type: mudsling.storage.Database
    db = None

    #: @type: mudsling.core.MUDSling
    game = None

    #: @type: int
    id = 0
    alive = False

    def __init__(self):
        self.db.register_task(self)

    def kill(self):
        """
        Kill this task. Children should take care to implement this according
        to their task mechanism!
        """
        self.alive = False
        self.db.remove_task(self.id)

    def server_startup(self):
        """
        Called on all registered tasks upon server startup.
        """

    def server_shutdown(self):
        """
        Called on all registered tasks upon server shutdown.
        """

    def __str__(self):
        return self.__class__.__name__

    def name(self):
        return "Task %d: %s" % (self.id, str(self))


class IntervalTask(BaseTask):
    """
    IntervalTask executes a callback at an interval.

    Example: IntervalTask(myFunc, 60) -- calls myFunc() every 60 seconds.
    """

    _transient_vars = ['_looper']

    _callback = None
    _interval = None
    _immediate = False
    _iterations = None
    _args = []
    _kwargs = {}

    #: @type: LoopingCall
    _looper = None

    _last_run_time = None
    _next_run_time = None
    _scheduled_time = None

    run_count = 0
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

    def __str__(self):
        return "%s (%s)" % (self.__class__.__name__, self._callback.__name__)

    @property
    def last_run_time(self):
        return self._last_run_time if self.run_count else None

    @property
    def next_run_time(self):
        if self.paused:
            return None
        return self._next_run_time

    def _schedule(self, interval=None):
        interval = max(0, interval if interval is not None else self._interval)
        if interval:  # None/0/False interval means it does not schedule.
            self._scheduled_time = time.time()
            now = self._immediate and not self.run_count
            self._looper = LoopingCall(self._run)
            self._next_run_time = time.time() + interval
            d = self._looper.start(interval, now=now)
            d.addErrback(self._errback)

    def kill(self):
        self._kill_looper()
        super(IntervalTask, self).kill()

    def _kill_looper(self):
        if self._looper is not None and self._looper.running:
            self._looper.stop()

    def pause(self):
        if not self.paused:
            last = self._last_run_time or self._scheduled_time or time.time()
            self._elapsed_at_pause = time.time() - last
            self.paused = True
            self._kill_looper()
            return True
        else:
            return False

    def unpause(self):
        if self.paused:
            del self.paused
            elapsed = self._elapsed_at_pause or 0
            self._schedule(self._interval - elapsed)

    def _run(self):
        self.run_count += 1
        self._last_run_time = time.time()
        #noinspection PyBroadException
        try:
            self._callback(*self._args, **self._kwargs)
        except:
            logging.error("Error in %s:\n%s" % (self, traceback.format_exc()))
        if self._iterations is not None and self.run_count >= self._iterations:
            self.kill()
        if self._elapsed_at_pause:
            del self._elapsed_at_pause
            self._kill_looper()
            self._schedule()

    def _errback(self, error):
        """
        @type error: twisted.python.failure.Failure
        """
        error.trap(Exception)
        if error.type == CancelledError:
            return
        tb = ''.join(traceback.format_exception(error.type, error.value,
                                                error.getTraceback()))
        logging.error("Error in %s:\n%s" % (self, tb))

    def server_startup(self):
        if not self.alive:
            return
        if not self._paused_at_shutdown:
            self.unpause()
        try:
            del self._paused_at_shutdown
        except AttributeError:
            pass
        super(IntervalTask, self).server_startup()

    def server_shutdown(self):
        self._paused_at_shutdown = self.paused
        self.pause()
        super(IntervalTask, self).server_shutdown()


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

    started = False

    def __init__(self):
        super(Task, self).__init__(self.run, None)

    def start(self, interval, iterations=None):
        if self.started:
            return False
        self.started = True
        if '_elapsed_at_pause' in self.__dict__:
            del self._elapsed_at_pause
        self._iterations = iterations
        self._interval = interval
        self.on_start()  # Task could modify settings here.
        self._schedule()

    def stop(self):
        self._kill_looper()
        if 'paused' in self.__dict__:
            del self.paused
        if '_elapsed_at_pause' in self.__dict__:
            del self._elapsed_at_pause
        if self.started:
            del self.started
            self.on_stop()

    def restart(self, interval=None, iterations=None):
        self.stop()
        interval = interval if interval is not None else self._interval
        self.start(interval, iterations=iterations)

    def pause(self):
        super(Task, self).pause()
        self.on_pause()

    def unpause(self):
        super(Task, self).unpause()
        self.on_unpause()

    def server_startup(self):
        super(Task, self).server_startup()
        self.on_server_startup()

    def server_shutdown(self):
        super(Task, self).server_shutdown()
        self.on_server_shutdown()

    def run(self):
        """
        This function is called when the task needs to run an iteration. This
        is generally called every <interval> seconds.
        """

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_unpause(self):
        pass

    def on_server_startup(self):
        pass

    def on_server_shutdown(self):
        pass
