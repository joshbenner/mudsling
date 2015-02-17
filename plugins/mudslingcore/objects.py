from collections import OrderedDict
import string

from mudsling.objects import BasePlayer, BaseCharacter, BaseObject
from mudsling.commands import all_commands
from mudsling.messages import Messages
from mudsling import parsers
from mudsling import locks
from mudsling.config import config
from mudsling.errors import AmbiguousMatch, FailedMatch

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.object as obj_utils

from objsettings import ObjSetting, ConfigurableObject
from mudslingcore import bans
from mudslingcore.channels import ChannelUser
from mudslingcore.genders import HasGender
from mudslingcore.senses import SensingObject, SensoryMedium
from mudslingcore.senses import Sensation, Sight, Speech
import mudslingcore.errors
from mudslingcore.areas import AreaExportableBaseObject
from mudslingcore.editor import EditorSessionHost
from mudslingcore.mail import MailRecipient
from mudslingcore import help
from mudslingcore.scripting import ScriptableObject

from mudslingcore import commands
from mudslingcore import ui


class InspectableObject(BaseObject):
    """
    Basic object that can be used with @show.
    """

    def show_details(self, who=None):
        """
        Key/value pairs to display when someone uses @show to inspect this.

        :param who: The object inspecting this object.
        """
        details = OrderedDict((
            ('Names', ', '.join(self.names)),
            ('Class', parsers.ObjClassStaticParser.unparse(self.__class__)),
            ('Owner', who.name_for(self.owner))
        ))
        return details


class CoreObject(SensoryMedium, InspectableObject, AreaExportableBaseObject,
                 ui.UsesUI):
    """
    The most basic object used by MUDSling Core.

    :ivar obscure: Object is visible but difficult to see. May be excluded
        from content lists.
    :type obscure: bool
    """
    obscure = False

    # Only special objects should be flagged as exportable to area files.
    area_exportable = False

    def area_export(self, sandbox):
        export = super(CoreObject, self).area_export(sandbox)
        if 'obscure' in self.__dict__:
            export['obscure'] = self.obscure
        return export

    def area_import(self, data, sandbox):
        super(CoreObject, self).area_import(data, sandbox)
        if 'obscure' in data:
            self.obscure = data['obscure']

    def show_in_contents_to(self, obj):
        return not self.obscure

    def contents_visible_to(self, obj):
        """
        Return the list of contents within self visible to the provided object.
        """
        default = lambda o: True
        return [c for c in self.contents
                if getattr(c, 'show_in_contents_to', default)(obj)]

    def contents_as_seen_by(self, obj):
        """
        Return the text describing the contents of self to the given object.
        """
        names = [' ' + o.contents_name(obj) for o
                 in self.contents_visible_to(obj)]
        return utils.string.columnize(names, 2) if names else " Nothing"

    @property
    def containing_room(self):
        """
        :returns: The first room found in this objects list of locations.
        :rtype: mudslingcore.topography.Room
        """
        import mudslingcore.rooms
        for loc in self.locations():
            if loc.isa(mudslingcore.rooms.Room):
                return loc
        return None

    @property
    def in_a_room(self):
        return self.containing_room is not None

    def emit(self, msg, exclude=None, location=None):
        """
        Version of emit which accepts sensations. If the input is a simple
        string, then the emit is assumed to be a :class:`Sight`.

        :param msg: Text or sensation to emit.
        :type msg: str or list or dict or Sensation
        :param exclude: List of objects to NOT notify of the emit.
        :type exclude: list or set or tuple or None
        :param location: Where the emission takes place.
        :type location: Object or SensoryMedium

        :return: The list of objects which were subject to the emission.
        :rtype: list
        """
        if location is None:
            location = self.location
        if isinstance(msg, (basestring, dict, list)):
            msg = Sight(msg)
        if isinstance(msg, Sensation):
            if location is not None and location.isa(SensoryMedium):
                return location.propagate_sensation(msg, exclude=exclude)
        else:
            return super(CoreObject, self).emit(msg, exclude, location)


class DescribableObject(CoreObject, ConfigurableObject):
    """
    An object that has a description and can be seen.

    :ivar desc: The description of the object.
    :type desc: str
    """
    desc = ""

    object_settings = (
        ObjSetting('desc', attr='desc', default=''),
    )

    def __init__(self, **kwargs):
        self.desc_mods = []
        super(DescribableObject, self).__init__(**kwargs)

    def area_export(self, sandbox):
        export = super(DescribableObject, self).area_export(sandbox)
        if 'desc' in self.__dict__:
            export['desc'] = self.desc
        return export

    def area_import(self, data, sandbox):
        super(DescribableObject, self).area_import(data, sandbox)
        if 'desc' in data:
            self.desc = data['desc']

    def seen_by(self, obj):
        """
        Return the string describing what the object sees when it looks at this
        object. Calling this method implies that the object actually looked at
        this object. If you need just the string, use as_seen_by().

        :param obj: The object looking at this object.

        :return: String describing this to the looking object.
        :rtype: str
        """
        return self.as_seen_by(obj)

    def as_seen_by(self, obj):
        """
        Return the string that would be output to the provided object if it
        looked at this object. Calling this method does not imply the look
        actually took place, so consider whether you should be calling this or
        seen_by().

        :param obj: The object that would be looking.
        :return: What the object would see.
        :rtype: str
        """
        return "%s\n%s" % (self.desc_title(obj), self.text_describe_to(obj))

    def desc_title(self, viewer):
        """
        Return the title to show before the description as seen by the passed
        object.
        """
        return viewer.name_for(self) if viewer is not None else self.name

    def describe_to(self, viewer):
        """
        :returns: Series of strings describing the object to the viewer.
        :rtype: collections.OrderedDict
        """
        desc = OrderedDict()
        desc['base'] = self.desc if self.desc else "You see nothing special."
        return desc

    def text_describe_to(self, viewer):
        desc = self.describe_to(viewer)
        return '\n'.join(desc.itervalues())


class Player(BasePlayer, ConfigurableObject, ChannelUser, EditorSessionHost,
             MailRecipient):
    """
    Core player class.
    """
    import commands.player as player_commands
    import commands.admin.system
    import commands.admin.perms
    import commands.admin.tasks
    import commands.admin.objects
    import commands.admin.players
    import commands.admin.areas
    import commands.scripting
    private_commands = all_commands(
        commands.admin.system,
        commands.admin.perms,
        commands.admin.tasks,
        commands.admin.objects,
        commands.admin.players,
        commands.admin.areas,
        commands.scripting,
        player_commands
    )
    del player_commands
    channels = {}

    messages = Messages({
        'teleport': {
            'actor': "You teleported {c$obj{n to {g$where{n.",
            'obj': "{c$actor{n teleported you to {g$where{n."
        },
        'teleport_failed': {
            'actor': "You fail to teleport {c$obj{n to {y$where{n."
        }
    })

    def __init__(self, **kwargs):
        super(Player, self).__init__(**kwargs)
        self.channels = {}

    def authenticate(self, password, session=None):
        applicable = bans.check_bans(session, self)
        if applicable:
            raise Exception("Connection banned: %s" % applicable[0])
        return super(Player, self).authenticate(password, session)

    def preemptive_command_match(self, raw):
        """
        :type raw: str
        """
        if raw.startswith(';') and self.has_perm("eval code"):
            import commands.admin.system
            return commands.admin.system.EvalCmd(raw, ';', raw[1:],
                                                 self.game, self.ref(),
                                                 self.ref())
        if raw.startswith('?'):
            import commands.player
            cmd = commands.player.HelpCmd(raw, '?', raw[1:], self.game,
                                          self.ref(), self.ref())
            cmd.match_syntax(cmd.argstr)
            return cmd
        return None

    def find_help_topic(self, search):
        # fltr = lambda e: e.lock.eval(e, self.ref())
        def fltr(e):
            return e.lock.eval(e, self.ref())
        try:
            topic = help.help_db.find_topic(search, entryFilter=fltr)
        except FailedMatch:
            topic = self.find_command_help_topic(search)
        return topic

    def find_command_help_topic(self, search):
        #: :type: list of BaseObject
        totry = [self]
        if self.is_possessing:
            totry.append(self.possessing)
        #: :type: list of mudsling.commands.Command
        cmds = []
        for obj in totry:
            cmds = obj.match_command(search)
            if len(cmds):
                break
        if len(cmds) == 1:
            _, cmd = cmds[0]
        elif len(cmds) > 1:
            raise AmbiguousMatch(query=search, matches=cmds)
        else:
            raise FailedMatch(query=search)
        topic = help.CommandHelpEntry(cmd)
        return topic


class Character(BaseCharacter, DescribableObject, SensingObject, HasGender):
    """Core character class."""

    # Do not export characters to area files.
    area_exportable = False

    import commands.admin.building as building_commands
    import commands.character as character_commands
    private_commands = all_commands(
        character_commands,

        # Building commands are administrative, but they apply in a "physical"
        # manner to the game world, so they are attached to the Character
        # instead of the Player.
        building_commands,
    )
    _say_cmd = character_commands.SayCmd
    _emote_cmd = character_commands.EmoteCmd
    _look_cmd = character_commands.LookCmd
    del character_commands, building_commands

    from rooms import Room, Exit
    object_settings = {
        # The classes to use when creating rooms and exits with @dig.
        ObjSetting(name='building.room_class',
                   type=type,
                   attr='building_room_class',
                   default=lambda o: config.getclass('Classes', 'room class'),
                   parser=parsers.ObjClassStaticParser),
        ObjSetting(name='building.exit_class',
                   type=type,
                   attr='building_exit_class',
                   default=lambda o: config.getclass('Classes', 'exit class'),
                   parser=parsers.ObjClassStaticParser),
    }
    del Room, Exit

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
        },
    })

    def is_possessable_by(self, player):
        """
        Core characters are ONLY possessable by players!
        :rtype: bool
        """
        return player.is_valid(Player)

    @property
    def player(self):
        """
        :rtype: Player or None
        """
        player = super(Character, self).player
        return player if player.is_valid(Player) else None

    def room_group(self, cls=None):
        from mudslingcore.rooms import RoomGroup
        cls = cls or RoomGroup
        for loc in self._location_walker():
            if loc.isa(RoomGroup) and loc.isa(cls):
                return loc
        return None

    def preemptive_command_match(self, raw):
        if raw.startswith('"'):
            return self._say_cmd(raw, '"', raw[1:], self.game,
                                 self.ref(), self.ref(), True)
        elif raw.startswith(':'):
            return self._emote_cmd(raw, ':', raw[1:], self.game,
                                   self.ref(), self.ref(), True)
        return None

    def match_literals(self, search, cls=None, err=False):
        if '->' in search and self.has_perm('use nested matching'):
            parts = filter(len, map(string.strip, search.split('->')))
            if len(parts) > 1:
                matches = self.match_object(parts[0], err=False)
                if len(matches) == 1:
                    for part in parts[1:]:
                        try:
                            matches = matches[0].match_contents(part)
                        except AttributeError:
                            matches = []
                            break
                    matches = obj_utils.filter_by_class(matches, cls=cls)
                    if err and len(matches) > 1:
                        raise AmbiguousMatch(query=search, matches=matches)
                    if matches:
                        return matches
        return super(Character, self).match_literals(search, cls=cls, err=err)

    def after_object_moved(self, moved_from, moved_to, by=None, via=None):
        if self.game.db.is_valid(moved_to, DescribableObject):
            cmd = self._look_cmd('look', 'look', '', self.game, self.ref(),
                                 self.ref())
            cmd.execute()

    def vision_sense(self, sensation):
        self.msg(sensation.content_for(self))

    def hearing_sense(self, sensation):
        content = self._format_msg(sensation.content_for(self))
        if isinstance(sensation, Speech):
            msg = [sensation.origin, ' says, "{c', content, '{n".']
        elif 'bare' in sensation.traits:
            msg = content
        else:
            msg = ["{mYou hear: {n", content]
        self.msg(msg)

    def say(self, speech):
        if not isinstance(speech, Speech):
            speech = Speech(str(speech), origin=self.ref())
        self.emit(speech, exclude=(self.ref(),))
        self.tell('You say, "{g', speech.content, '{n".')

    def _prepare_emote(self, pose, sep=' ', prefix='', suffix='',
                       show_name=True):
        msg = [prefix, self.ref() if show_name else '', sep]
        if isinstance(pose, list):
            msg.extend(pose)
        else:
            msg.append(pose)
        if suffix:
            msg.extend((sep, suffix))
        return msg

    def emote(self, pose, sep=' ', prefix='', suffix='', show_name=True):
        self.emit(self._prepare_emote(pose, sep, prefix, suffix, show_name))


class Thing(DescribableObject, ScriptableObject):
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
        },
        'teleport_out': {
            'actor': "{bYou dematerialize.",
            '*': "{c$actor {bvanishes."
        },
        'teleport_in': {
            'actor': "{bYou materialize in {c$dest{b.",
            '*': "{c$actor {bmaterializes."
        },
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
    can_close = True

    @property
    def opened(self):
        return self._opened if self.can_close else True

    @property
    def closed(self):
        return not self._opened

    def propagate_sensation_up(self, sensation):
        return self.opened

    def open(self, opened_by=None):
        """
        Opens the container.

        Will emit the 'open' message with opened_by as the actor if specified.

        :param opened_by: The object responsible for opening the container.
        :type opened_by: mudsling.objects.Object
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

        :param closed_by: The object responsible for closing the container.
        :type closed_by: mudsling.objects.Object
        """
        if self._opened:
            self._opened = False
            if closed_by is not None and closed_by.location == self.location:
                self.emit_message('close', actor=closed_by)
            else:
                self.emit([self.ref(), ' closes.'])

    def desc_title(self, viewer):
        name = super(Container, self).desc_title(viewer)
        if self.can_close:
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

    def describe_to(self, viewer):
        desc = super(Container, self).describe_to(viewer)
        if self._opened:
            desc['open container contents'] = \
                'Contents:\n' + self.contents_as_seen_by(viewer)
        return desc


class LockableContainer(Container):
    """
    A container that can be locked, though this class provides no locking
    mechanism.
    """
    locked = False

    def open(self, opened_by=None):
        if not self.opened:
            if self.locked:
                name = (self.name if opened_by is None
                        else opened_by.name_for(self))
                raise mudslingcore.errors.ContainerLocked(
                    '%s is locked' % name)
            super(LockableContainer, self).open(opened_by=opened_by)
