from mudsling.commands import Command
from mudsling import locks

from pathfinder import conditions


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


class PhysicalActionCommand(Command):
    """
    A command which requires the character to be able to move or act
    physically. These commands will fail if the character is unconscious,
    restrained, etc.
    """

    lock = locks.all_pass

    def prepare(self):
        """
        Make sure the character can physically complete this command.
        :return: True if the character is physically capable.
        :rtype: bool
        """
        #: :type: pathfinder.characters.Character
        actor = self.actor
        return not actor.has_condition(conditions.Incapable)


class MovementActionCommand(Command):
    """
    A command which requires the ability to move and (probably) consumes a
    movement action during a combat turn.
    """

    lock = locks.all_pass

    def prepare(self):
        #: :type: pathfinder.characters.Character
        actor = self.actor
        return not actor.has_condition(conditions.Immobilized)
