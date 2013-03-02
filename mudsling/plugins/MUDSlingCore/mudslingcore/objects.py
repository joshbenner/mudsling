from mudsling.objects import BasePlayer, BaseCharacter
from mudsling.objects import Object
from mudsling.commands import allCommands

import commands.admin.system
import commands.admin.perms
import commands.admin.tasks
import commands.admin.objects
import commands.ooc


class Thing(Object):
    """
    The basic object in the MUDSling core game world.

    Features:
        - Description

    @ivar desc: The description of the object.
    @type desc: str
    """

    desc = ""

    #: @type: Object
    location = None  # Here for type resolution in editors that support it.

    def seenBy(self, obj):
        """
        Return the string describing what the object sees when it looks at this
        object. Calling this method implies that the object actually looked at
        this object. If you need just the string, use asSeenBy().

        @param obj: The object looking at this object.
        @type obj: Thing
        @return: String describing this to the looking object.
        @rtype: str
        """
        return self.asSeenBy(obj)

    def asSeenBy(self, obj):
        """
        Return the string that would be output to the provided object if it
        looked at this object. Calling this method does not imply the look
        actually took place, so consider whether you should be calling this or
        seenBy().

        @param obj: The object that would be looking.
        @return: What the object would see.
        @rtype: str
        """
        return "%s\n%s" % (self.name, self.desc)


class Player(BasePlayer):
    commands = allCommands(
        commands.admin.system,
        commands.admin.perms,
        commands.admin.tasks,
        commands.admin.objects,
        commands.ooc
    )

    def preemptiveCommandMatch(self, raw):
        """
        @type raw: str
        """
        if raw.startswith(';') and self.hasPerm("eval code"):
            cmd = commands.admin.system.EvalCmd(raw, ';', raw[1:],
                                                self.game, self.ref(),
                                                self.ref())
            return cmd
        return None


class Character(Thing, BaseCharacter):
    pass
