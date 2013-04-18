from mudsling.commands import Command
from mudsling import tasks
from mudsling import errors
from mudsling import locks

from . import ui  # Use the admin package ui.

manageTasks = locks.Lock('perm(manage tasks)')


class TasksCmd(Command):
    """
    @tasks

    List all tasks registered with the database.
    """
    aliases = ('@tasks',)
    lock = manageTasks

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """

        format_next_run = lambda t: ('(paused)' if t is None
                                     else ui.format_timestamp(t))

        table = ui.Table(
            [
                ui.Column("ID", data_key='id', align='r'),
                ui.Column("Task", data_key='__str__', width='*', align='l'),
                ui.Column("Interval", data_key='_interval', align='r',
                          cell_formatter=ui.format_dhms),
                ui.Column("Last Run", data_key="last_run_time", align='l',
                          cell_formatter=ui.format_timestamp),
                ui.Column("Next Run", data_key="next_run_time", align='l',
                          cell_formatter=format_next_run),
            ]
        )
        table.add_rows(*self.game.db.tasks.itervalues())
        actor.msg(ui.report("Tasks", table))


class KillTaskCmd(Command):
    """
    @kill-task <id>

    Kill the specified task.
    """
    aliases = ('@kill-task', '@killtask', '@kill')
    lock = manageTasks
    syntax = r"<id:\d+>"

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        try:
            task = self.game.db.get_task(int(args['id']))
            task.kill()
        except Exception as e:
            actor.msg("{r%s" % e.message)
            return

        if task.alive:
            actor.msg("{rSomething didn't work: Task is still alive.")
        else:
            actor.msg("{c%s {mhas been {ykilled." % task.name())


class PauseTaskCmd(Command):
    """
    @pause-task <id>

    Pauses the specified task.
    """
    aliases = ('@pause-task', '@pausetask')
    lock = manageTasks
    syntax = r"<id:\d+>"

    def run(self, this, actor, args):
        try:
            #: @type: mudsling.tasks.IntervalTask
            task = self.game.db.get_task(int(args['id']))
            if not isinstance(task, tasks.IntervalTask):
                raise errors.InvalidTask("Only IntervalTask tasks may be "
                                         "paused or unpaused.")
        except Exception as e:
            actor.msg("{r%s" % e.message)
            return

        if task.paused:
            actor.msg("{y%s is already paused." % task.name())
        else:
            task.pause()
            actor.msg("{c%s {mis now {ypaused." % task.name())


class UnpauseTaskCmd(Command):
    """
    @unpause-task <id>

    Un-pauses the specified task.
    """
    aliases = ('@unpause-task', '@resume-task', '@unpausetask', '@resumetask')
    lock = manageTasks
    syntax = r"<id:\d+>"

    def run(self, this, actor, args):
        try:
            #: @type: mudsling.tasks.IntervalTask
            task = self.game.db.get_task(int(args['id']))
            if not isinstance(task, tasks.IntervalTask):
                raise errors.InvalidTask("Only IntervalTask tasks may be "
                                         "paused or unpaused.")
        except Exception as e:
            actor.msg("{r%s" % e.message)
            return

        if task.paused:
            task.unpause()
            actor.msg("{c%s {mis now {grunning." % task.name())
        else:
            actor.msg("{y%s is not paused." % task.name())
