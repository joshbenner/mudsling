from mudsling.objects import BasePlayer, BaseCharacter, Object
from mudsling.commands import all_commands
from mudsling.messages import Messages
from mudsling import parsers
from mudsling import locks

from mudsling import utils
import mudsling.utils.string

from objsettings import ObjSetting, ConfigurableObject
from mudslingcore import bans

from mudslingcore import commands
import commands.admin.system
import commands.admin.perms
import commands.admin.tasks
import commands.admin.objects
import commands.admin.players
import commands.character


class DescribableObject(Object):
    """
    An object that has a description and can be seen.

    @ivar desc: The description of the object.
    @type desc: str
    """
    desc = ""

    def seen_by(self, obj):
        """
        Return the string describing what the object sees when it looks at this
        object. Calling this method implies that the object actually looked at
        this object. If you need just the string, use as_seen_by().

        @param obj: The object looking at this object.

        @return: String describing this to the looking object.
        @rtype: str
        """
        return self.as_seen_by(obj)

    def as_seen_by(self, obj):
        """
        Return the string that would be output to the provided object if it
        looked at this object. Calling this method does not imply the look
        actually took place, so consider whether you should be calling this or
        seen_by().

        @param obj: The object that would be looking.
        @return: What the object would see.
        @rtype: str
        """
        return "%s\n%s" % (self.desc_title(obj), self.describe_to(obj))

    def desc_title(self, obj):
        """
        Return the title to show before the description as seen by the passed
        object.
        """
        return obj.name_for(self) if obj is not None else self.name

    def describe_to(self, obj):
        """
        Return the string describing this object to the passed object.
        """
        return self.desc if self.desc else "You see nothing special."

    def contents_visible_to(self, obj):
        """
        Return the list of contents within self visible to the provided object.
        """
        return list(self.contents)

    def contents_as_seen_by(self, obj):
        """
        Return the text describing the contents of self to the given object.
        """
        names = [' ' + obj.name_for(o) for o in self.contents_visible_to(obj)]
        return utils.string.columnize(names, 2) if names else " Nothing"


class Player(BasePlayer, ConfigurableObject):
    """
    Core player class.
    """
    import commands.player
    private_commands = all_commands(
        commands.admin.system,
        commands.admin.perms,
        commands.admin.tasks,
        commands.admin.objects,
        commands.admin.players,
        commands.player
    )

    def authenticate(self, password, session=None):
        applicable = bans.check_bans(session, self)
        if applicable:
            raise Exception("Connection banned: %s" % applicable[0])
        return super(Player, self).authenticate(password, session)

    def preemptive_command_match(self, raw):
        """
        @type raw: C{str}
        """
        if raw.startswith(';') and self.has_perm("eval code"):
            return commands.admin.system.EvalCmd(raw, ';', raw[1:],
                                                 self.game, self.ref(),
                                                 self.ref())
        if raw.startswith('?'):
            cmd = commands.player.HelpCmd(raw, '?', raw[1:], self.game,
                                          self.ref(), self.ref())
            cmd.match_syntax(cmd.argstr)
            return cmd
        return None


class Character(BaseCharacter, DescribableObject, ConfigurableObject):
    """
    Core character class.
    """
    # Try to avoid some circular imports.
    from topography import Room, Exit
    import commands.admin.building

    private_commands = all_commands(
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
        'say': {
            'actor': 'You say, "{g$speech{n".',
            '*': '{c$actor{n says, "{c$speech{n".'
        },
        'teleport_out': {
            'actor': "{bYou dematerialize.",
            '*': "{c$actor {bvanishes."
        },
        'teleport_in': {
            'actor': "{bYou materialize in {c$dest{b.",
            '*': "{c$actor {bmaterializes."
        }
    })

    def is_possessable_by(self, player):
        """
        Core characters are ONLY possessable by players!
        @rtype: bool
        """
        return player.is_valid(Player)

    @property
    def player(self):
        """
        @rtype: L{Player} or C{None}
        """
        player = super(Character, self).player
        return player if player.is_valid(Player) else None

    def preemptive_command_match(self, raw):
        if raw.startswith('"'):
            return commands.character.SayCmd(raw, '"', raw[1:], self.game,
                                             self.ref(), self.ref(), True)
        elif raw.startswith(':'):
            return commands.character.EmoteCmd(raw, ':', raw[1:], self.game,
                                               self.ref(), self.ref(), True)
        return None


class Thing(DescribableObject):
    """
    The basic object in the MUDSling core game world.

    Can be picked up, dropped, and given.
    """
    import commands.thing

    public_commands = all_commands(
        commands.thing
    )

    create_lock = locks.Lock('perm(create things)')

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
        },
        'give': {
            'actor': "You hand $this to $recipient.",
            'recipient': "$actor hands you $this.",
            '*': "$actor hands $this to $recipient."
        }
    })


class Container(Thing):
    """
    The basic container-like thing.

    Can be opened or closed, and provides commands for putting things in it.
    """
    import commands.container
    public_commands = all_commands(commands.container)
    messages = Messages({
        'close': {
            'actor': 'You close $this.',
            '*': '$actor closes $this.'
        },
        'open': {
            'actor': 'You open $this.',
            '*': '$actor opens $this.'
        },
        'add': {
            'actor': 'You put $thing in $this.',
            '*': '$actor puts $thing in $this.'
        },
        'add_fail': {
            'actor': 'You cannot put $thing in $this.'
        },
        'remove': {
            'actor': 'You remove $thing from $this.',
            '*': '$actor removes $thing from $this.'
        },
        'remove_fail': {
            'actor': 'You cannot remove $thing from $this.'
        }
    })
    _opened = False

    @property
    def opened(self):
        return self._opened

    @property
    def closed(self):
        return not self._opened

    def open(self, opened_by=None):
        """
        Opens the container.

        Will emit the 'open' message with opened_by as the actor if specified.

        @param opened_by: The object responsible for opening the container.
        @type opened_by: L{mudsling.objects.Object}
        """
        if not self._opened:
            self._opened = True
            if opened_by is not None and opened_by.location == self.location:
                self.emit_message('open', actor=opened_by)
            else:
                self.emit([self.ref(), ' opens.'])

    def close(self, closed_by=None):
        """
        Closes the container. Emits message if `closed_by` is specified.

        @param closed_by: The object responsible for closing the container.
        @type closed_by: L{mudsling.objects.Object}
        """
        if self._opened:
            self._opened = False
            if closed_by is not None and closed_by.location == self.location:
                self.emit_message('close', actor=closed_by)
            else:
                self.emit([self.ref(), ' closes.'])

    def desc_title(self, obj):
        name = super(Container, self).desc_title(obj)
        if self._opened:
            name += ' {g(open)'
        else:
            name += ' {y(closed)'
        return name

    def contents_visible_to(self, obj):
        if self._opened or obj in self.contents:
            return super(Container, self).contents_visible_to(obj)
        else:
            return []

    def describe_to(self, obj):
        desc = [super(Container, self).describe_to(obj)]
        if self._opened:
            desc.append('Contents:')
            desc.append(self.contents_as_seen_by(obj))
        return '\n'.join(desc)
