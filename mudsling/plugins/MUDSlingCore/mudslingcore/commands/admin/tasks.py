from mudsling.commands import Command

from . import ui  # Use the admin package ui.


class TasksCmd(Command):
    """
    @tasks

    List all tasks registered with the database.
    """
    aliases = ('@tasks',)
    required_perm = 'manage tasks'

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        table = ui.Table(
            [
                ui.Column("ID", data_key='id', align='r'),
                ui.Column("Task", data_key='__str__', width='*', align='l'),
                ui.Column("Interval", data_key='_interval', align='r',
                          cell_formatter=ui.format_dhms),
                ui.Column("Last Run", data_key="last_run_time", align='l',
                          cell_formatter=ui.format_timestamp),
                ui.Column("Next Run", data_key="next_run_time", align='l',
                          cell_formatter=ui.format_timestamp),
            ]
        )
        for task in self.game.db.tasks.itervalues():
            table.addRow(task)

        actor.msg(ui.report("Tasks", table))
