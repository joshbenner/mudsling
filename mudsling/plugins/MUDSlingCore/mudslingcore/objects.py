from mudsling.objects import BasePlayer, BaseCharacter, Object
from mudsling.commands import allCommands
from mudsling.messages import Messages
from mudsling import parsers
from mudsling import locks

from mudsling import utils
import mudsling.utils.string

from objsettings import ObjSetting, ConfigurableObject
from bans import checkBans

from mudslingcore import commands
import commands.admin.system
import commands.admin.perms
import commands.admin.tasks
import commands.admin.objects
import commands.admin.players
import commands.player
import commands.character


class DescribableObject(Object):
    """
    An object that has a description and can be seen.

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
        return "%s\n%s" % (self.descTitle(obj), self.describeTo(obj))

    def descTitle(self, obj):
        """
        Return the title to show before the description as seen by the passed
        object.
        """
        return obj.nameFor(self) if obj is not None else self.name

    def describeTo(self, obj):
        """
        Return the string describing this object to the passed object.
        """
        return self.desc if self.desc else "You see nothing special."

    def contentsVisibleTo(self, obj):
        """
        Return the list of contents within self visible to the provided object.
        """
        return list(self.contents)

    def contentsAsSeenBy(self, obj):
        """
        Return the text describing the contents of self to the given object.
        """
        names = [' ' + obj.nameFor(o) for o in self.contentsVisibleTo(obj)]
        return utils.string.columnize(names, 2) if names else " Nothing"


class Thing(DescribableObject):
    """
    The basic object in the MUDSling core game world.

    Can be picked up, dropped, and given.
    """
    import commands.thing

    public_commands = allCommands(
        commands.thing
    )

    createLock = locks.Lock('perm(create things)')

    messages = Messages({
        'drop': {
            'actor': "You drop $this.",
            '*': "$actor drops $this."
        },
        'drop_fail': {
            'actor': "You can't seem to drop $this.",
            '*': "$actor tries to drop $this, but fails."
        },
        'take': {
            'actor': "You take $this.",
            '*': "$actor takes $this."
        },
        'take_fail': {
            'actor': "You try to pick up $this, but fail.",
            '*': "$actor tires to pick up $this, but fails."
        }
    })


class Player(BasePlayer, ConfigurableObject):
    """
    Core player class.
    """
    private_commands = allCommands(
        commands.admin.system,
        commands.admin.perms,
        commands.admin.tasks,
        commands.admin.objects,
        commands.admin.players,
        commands.player
    )

    def authenticate(self, password, session=None):
        bans = self.db.getSetting('bans', default=[])
        applicable = checkBans(session, bans)
        if applicable:
            raise Exception("Connection banned: %s" % applicable[0].reason)
        return super(Player, self).authenticate(password, session)

    def preemptiveCommandMatch(self, raw):
        """
        @type raw: C{str}
        """
        if raw.startswith(';') and self.hasPerm("eval code"):
            return commands.admin.system.EvalCmd(raw, ';', raw[1:],
                                                 self.game, self.ref(),
                                                 self.ref())
        if raw.startswith('?'):
            cmd = commands.player.HelpCmd(raw, '?', raw[1:], self.game,
                                          self.ref(), self.ref())
            cmd.matchSyntax(cmd.argstr)
            return cmd
        return None


class Character(BaseCharacter, DescribableObject, ConfigurableObject):
    """
    Core character class.
    """
    # Try to avoid some circular imports.
    from topography import Room, Exit
    import commands.admin.building

    private_commands = allCommands(
        commands.character,

        # Building commands are administrative, but they apply in a "physical"
        # manner to the game world, so they are attached to the Character
        # instead of the Player.
        commands.admin.building,
    )

    object_settings = {
        # The classes to use when creating rooms and exits with @dig.
        ObjSetting(name='building.room_class',
                   type=type,
                   attr='building_room_class',
                   default=Room,
                   parser=parsers.ObjClassStaticParser),
        ObjSetting(name='building.exit_class',
                   type=type,
                   attr='building_exit_class',
                   default=Exit,
                   parser=parsers.ObjClassStaticParser),
    }

    messages = Messages({
        'teleport_out': {
            'actor': "{bYou dematerialize.",
            '*': "{c$actor {bvanishes."
        },
        'teleport_in': {
            'actor': "{bYou materialize in {c$dest{b.",
            '*': "{c$actor {bmaterializes."
        }
    })

    def possessableBy(self, player):
        """
        Core characters are ONLY possessable by players!
        @rtype: bool
        """
        return player.isValid(Player)

    @property
    def player(self):
        """
        @rtype: L{Player} or C{None}
        """
        player = super(Character, self).player
        return player if player.isValid(Player) else None
