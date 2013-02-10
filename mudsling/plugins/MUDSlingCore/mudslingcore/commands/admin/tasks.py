from mudsling.commands import Command


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
