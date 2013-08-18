import mudsling.locks
import mudsling.commands

import pathfinder.conditions


class LevellingCommand(mudsling.commands.Command):
    """
    A command which can only be used while levelling up.
    """

    #: :type: pathfinder.characters.Character
    obj = None
    lock = mudsling.locks.all_pass
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


class CombatCommand(mudsling.commands.Command):
    """
    A generic combat command.
    """
    action_type = 'standard'


class PhysicalCombatCommand(mudsling.commands.Command):
    """
    A command which requires the character to be able to move or act
    physically. These commands will fail if the character is unconscious,
    restrained, etc.
    """

    lock = mudsling.locks.all_pass

    def prepare(self):
        """
        Make sure the character can physically complete this command.
        :return: True if the character is physically capable.
        :rtype: bool
        """
        #: :type: pathfinder.characters.Character
        actor = self.actor
        return not actor.has_condition(pathfinder.conditions.Incapable)


class MovementCombatCommand(mudsling.commands.Command):
    """
    A command which requires the ability to move and (probably) consumes a
    movement action during a combat turn.
    """

    lock = mudsling.locks.all_pass

    def prepare(self):
        #: :type: pathfinder.characters.Character
        actor = self.actor
        return not actor.has_condition(pathfinder.conditions.Immobilized)
