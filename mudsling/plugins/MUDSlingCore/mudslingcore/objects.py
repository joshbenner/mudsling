from mudsling.objects import BasePlayer, BaseCharacter
from mudsling.objects import Object as LocatedObject
from .commands import admin as admin_commands
from .commands import ooc as ooc_commands


class Object(LocatedObject):
    """
    The basic object in the MUDSling core game world.

    @ivar desc: The description of the object.
    @type desc: str
    """

    desc = ""

    def seenBy(self, obj):
        """
        Return the string describing what the object sees when it looks at this
        object. Calling this method implies that the object actually looked at
        this object. If you need just the string, use asSeenBy().

        @param obj: The object looking at this object.
        @type obj: Object
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
    commands = [
        admin_commands.EvalCmd,
        admin_commands.RolesCmd,
        ooc_commands.AnsiCmd
    ]

    def preemptiveCommandMatch(self, input):
        """
        @type input: mudsling.parse.ParsedInput
        """
        if input.raw.startswith(';') and self.hasPerm("eval code"):
            input.cmdstr = ';'
            input.argstr = input.raw[1:]
            return admin_commands.EvalCmd
        return None


class Character(BaseCharacter):
    pass
