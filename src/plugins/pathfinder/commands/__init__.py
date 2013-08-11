from mudsling.commands import Command
from mudsling import locks


class LevellingCommand(Command):
    """
    A command which can only be used while levelling up.
    """

    #: :type: pathfinder.characters.Character
    obj = None
    lock = locks.all_pass
    not_levelling_msg = None

    def prepare(self):
        if not self.obj.levelling_up():
            if self.not_levelling_msg is None:
                msg = "{rYou may only use %s while levelling up." % self.cmdstr
            else:
                msg = self.not_levelling_msg
            self.actor.tell(msg)
            return False
        return True


class SomaticCommand(Command):
    """
    A command which requires the character to be able to move or act
    physically. These commands will fail if the character is unconscious,
    restrained, etc.
    """

    lock = locks.all_pass

    def prepare(self):
        """
        Make sure the character can physically complete this command.
        :return:
        """
        pass
