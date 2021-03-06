"""
Rooms and exits.
"""
import itertools
import re

from mudsling.objects import Object as LocatedObject
from mudsling.messages import Messages
from mudsling.commands import Command
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from mudslingcore.objects import DescribableObject
from mudslingcore.objsettings import ConfigurableObject, ObjSetting
import mudslingcore.areas as areas


# noinspection PyShadowingBuiltins
class ExitCmd(Command):
    """
    <exit-name>

    Proceed through the named exit.
    """
    def run(self, this, actor, args):
        """
        :param this: The exit object.
        :type this: Exit

        :param actor: The object moving through the exit.
        :type actor: mudsling.objects.Object

        :param args: Unused.
        """
        this.invoke(actor)


# noinspection PyShadowingBuiltins
class Room(DescribableObject):
    """
    A standard room.

    Features:
    * Looking at things
    * Exits
    """
    desc = "A very nondescript room."
    #: :type: list of Exit
    exits = []
    senses = {'hearing', 'vision'}
    _exit_cmd = ExitCmd
    room_title_format = '{y%(name)'

    area_exportable = True

    object_settings = {
        ObjSetting('room_title_format', str, attr='room_title_format')
    }

    def __init__(self, **kwargs):
        super(Room, self).__init__(**kwargs)
        #: :type: list of Exit
        self.exits = []

    def exit_cmd(self, exit, actor=None):
        return exit._exit_cmd or self._exit_cmd or ExitCmd

    def area_export(self, sandbox):
        export = super(Room, self).area_export(sandbox)
        if 'exits' in self.__dict__:
            export['exits'] = areas.export_object_list(self.exits, sandbox)
        return export

    def area_import(self, data, sandbox):
        super(Room, self).area_import(data, sandbox)
        for exit_record in data.get('exits', []):
            exit = areas.import_area_object(exit_record, sandbox)
            self.exits.append(exit)

    @property
    def room_group(self):
        """:rtype: RoomGroup"""
        if self.has_location and self.location.isa(RoomGroup):
            return self.location
        return None

    def room_groups(self, cls=None):
        cls = cls or RoomGroup
        return [l for l in self.locations() if l.isa(cls)]

    def exposed_context(self):
        """
        Expose exits as context.
        """
        context = super(Room, self).exposed_context()
        context.extend(self.exits)
        return context

    def match_exits(self, search, exactOnly=True):
        return self._match(search, self.exits, exactOnly=exactOnly)

    def filter_exits(self, filterfunc):
        """
        Retrieves a list of exits matching the specified filters.
        :param filterfunc: Callback used to filter the list of exits.
        """
        return filter(filterfunc, self.exits)

    def exits_to(self, destination):
        """
        Find any exits leading to the specified destination.

        :param destination: The destination the sought exit leads to.
        :type destination: Room

        :return: List of exits leading to the destination.
        :rtype: list
        """
        destination = destination.ref()
        return self.filter_exits(lambda e: e.dest == destination)

    def handle_unmatched_input_for(self, actor, raw):
        matches = self.match_exits(raw)
        if len(matches) == 1:
            f = self.exit_cmd(matches[0], actor=actor)
            return f(raw, raw, raw, self.game, matches[0], actor)
        elif len(matches) > 1:
            msg = "Which way? {raw!r} matches: {exits}".format(
                raw=raw,
                exits=utils.string.english_list(
                    matches, formatter=lambda e: actor.name_for(e))
            )
            raise errors.CommandError(msg)
        else:
            return super(Room, self).handle_unmatched_input(raw)

    def allow_enter(self, what, exit=None):
        """
        Determines if what may enter this room via the given exit.
        :rtype: bool
        """
        return what.is_valid(LocatedObject)

    def allow_leave(self, what, exit=None):
        """
        Determines if what may leave this room via the given exit.
        """
        return True

    def enter_allowed(self, what, exit=None):
        """
        Exits call this to ask the room if it has allowed an actual attempt by
        what to transit the exit. This gives the room the opportunity to emit
        messages to the object, itself, etc. apart from the actual evaluation
        of whether the entrance is permitted.
        """
        return self.allow_enter(what, exit=exit)

    def leave_allowed(self, what, exit=None):
        """
        :see: Room.enter_allowed
        """
        return self.allow_leave(what, exit=exit)

    def add_exit(self, exit, by=None):
        if exit.is_valid(Exit):
            self.exits.append(exit)
            if self.db.is_valid(exit.dest, cls=Room):
                exit.dest.entrance_added(exit, by=by)

    def entrance_added(self, exit, by=None):
        """
        Called when another room adds an exit leading to this room.
        :param exit: The exit that was added.
        """

    def remove_exit(self, exit, delete=True, by=None):
        if exit in self.exits:
            self.exits.remove(exit)
            if exit.is_valid(Exit):
                if self.db.is_valid(exit.dest, cls=Room):
                    exit.dest.entrance_removed(exit, by=by)
            if exit.is_valid() and delete:
                exit.delete()

    def entrance_removed(self, exit, by=None):
        """
        Called when another room removes an exit leading to this room.
        :param exit: The exit that was removed.
        """

    def desc_tokens(self, viewer):
        group = self.room_group
        tokens = {'name': self.desc_title(viewer)}
        if group is not None:
            tokens['group'] = (viewer.name_for(group) if viewer is not None
                               else group.name)
            tokens.update(group.room_desc_tokens(self, viewer))
        return tokens

    _fmt_cleanup_re = re.compile(r'(%\([^)]+\))\B')

    @classmethod
    def _cleanup_format(cls, fmt):
        return cls._fmt_cleanup_re.sub(r'\1s', fmt)

    @classmethod
    def _process_tokens(cls, text, tokens):
        try:
            return cls._fmt_cleanup_re.sub(r'\1s', text) % tokens
        except (ValueError, KeyError):
            return text

    def as_seen_by(self, obj):
        tokens = self.desc_tokens(obj)
        title_fmt = self.get_room_setting('room_title_format',
                                          default='%(name)')
        title = self._process_tokens(title_fmt, tokens)
        desc = self._process_tokens(self.text_describe_to(obj), tokens)
        contents = self.contents_as_seen_by(obj)
        exits = self.exits_as_seen_by(obj)
        out = '%s\n%s' % (title, desc)
        if contents:
            out += '\n\n' + contents
        if exits:
            out += '\n\n' + exits
        return out

    def contents_as_seen_by(self, obj):
        """
        Return the contents of the room as seen by the passed object.
        """
        contents = self.contents_visible_to(obj)
        if obj in contents:
            contents.remove(obj)
        if contents:
            fmt = "{c%s{n"
            names = utils.string.english_list([fmt % c.contents_name(obj)
                                               for c in contents])
            return "You see %s here." % names
        else:
            return ''

    def exits_as_seen_by(self, obj):
        if not self.exits:
            return "You do not see any obvious exits."
        names = "{c | {n".join([e.exit_list_name() for e in self.exits])
        return "{c[{n %s {c]" % names

    def get_room_setting(self, attr, default=None):
        """
        Get a setting that can be inherited from the room group, or overridden
        on the room itself.

        Setting priority:
        1. Set on room instance.
        2. Set on some parent room group instance.
        3. Set on some parent room group class.
        4. Set on room class.
        """
        if attr not in self.__dict__:
            g = self.room_group
            if g is not None:
                v = g.get_group_setting(attr)
                if v is not None:
                    return v
        return getattr(self, attr, default)


# noinspection PyShadowingBuiltins
class Exit(areas.AreaExportableBaseObject):
    """
    Core exit class.

    Transisions an object between two rooms.

    :ivar source: The room where this exit exists.
    :ivar dest: The room to which this exit leads.
    """

    #: :type: Room
    source = None
    #: :type: Room
    dest = None
    _exit_cmd = None

    messages = Messages({
        'leave': {
            'actor': None,
            '*': "$actor leaves for $exit.",
        },
        'leave_failed': {'actor': "You can't go that way."},
        'arrive': {  # Shown in destination when transiting this exit.
            'actor': None,
            '*': "$actor has arrived."
        },
    })

    def area_export(self, sandbox):
        export = super(Exit, self).area_export(sandbox)
        if self.game.db.is_valid(self.source, areas.AreaExportableBaseObject):
            export['source'] = areas.export_weak_ref(self.source)
        if self.game.db.is_valid(self.dest, areas.AreaExportableBaseObject):
            export['dest'] = areas.export_weak_ref(self.dest)
        return export

    def area_import(self, data, sandbox):
        super(Exit, self).area_import(data, sandbox)
        if 'source' in data:
            areas.import_weak_ref(self.ref(), 'source', data['source'],
                                  sandbox)
        if 'dest' in data:
            areas.import_weak_ref(self.ref(), 'dest', data['dest'], sandbox)

    def emit_message(self, key, exclude=None, **keywords):
        """
        Emit a messate template to the exit's room.

        Will try to emit the same message key with the suffix '_other_side' on
        the exit's counterpart on the other side.

        :param key: The message key to emit.
        :param exclude: Any objects to exclude from receipt of the message.
        :param keywords: Keywords for use in the template.

        :return: List of those objects that received the message.
        :rtype: list
        """
        suffix = '_other_side'
        original = not key.endswith(suffix)
        room = self.source
        keywords['this'] = self.ref()
        keywords['room'] = room
        if original:
            keywords['origin_exit'] = keywords['this']
            keywords['origin_room'] = room
        msg = self.get_message(key, **keywords)
        receivers = room.msg_contents(msg, exclude=exclude)
        counterpart = self.counterpart
        if original and counterpart is not None:
            receivers.extend(self.counterpart.emit_message(key + suffix,
                                                           exclude=exclude,
                                                           **keywords))
        return receivers

    @property
    def counterpart(self):
        """
        Find an exit's counterpart in its destination.
        :return: The corresponding exit back to this exit's source from this
            exit's destination.
        :rtype: Exit or None
        """
        v = self.game.db.is_valid
        if v(self.source, Room) and v(self.dest, Room):
            counterparts = self.dest.exits_to(self.source)
            if len(counterparts) > 0:
                return counterparts[0]
        return None

    def invoke(self, obj):
        """
        Check if obj may pass through this exit, and if so, pass obj through
        this exit.

        :param obj: The object attempting to pass through the exit.
        :type obj: mudsling.objects.Object
        """
        if self.transit_allowed(obj):
            self._move(obj)
        else:
            obj.emit(self.get_message('leave_failed',
                                      actor=obj,
                                      exit=self.ref(),
                                      dest=self.dest,
                                      room=self.source,
                                      source=self.source))

    def _invalid_enter_allowed(self, what, exit=None):
        """
        This is used as the enter_allowed call in the event that the
        destination is not a valid Room.
        """
        what.msg("You cannot walk through an exit to nowhere!")
        return False

    def transit_allowed(self, obj):
        """
        Returns True if obj has been allowed to continue on an actual attempt
        to transit the exit. This is not a simple permission check, it is a
        permission check AND resulting in-game effects of the actual attempt to
        transit the exit.

        :see: Room.leave_allowed and Room.enter_allowed

        :param obj: The object under consideration.
        :type obj: mudsling.objects.Object
        """
        # Acquire references to the transition attempt result methods from the
        # involved rooms, else placeholder functions.
        leave_allowed = (obj.location.leave_allowed
                         if obj.has_location and obj.location.is_valid(Room)
                         else lambda w, e: True)
        enter_allowed = (self.dest.enter_allowed
                         if self.dest is not None and self.dest.is_valid(Room)
                         else self._invalid_enter_allowed)
        me = self.ref()
        return leave_allowed(obj, me) and enter_allowed(obj, me)

    def _move(self, obj):
        """
        Pass the object through this exit to its destination.
        No permission checks -- just do it!

        :param obj: The object to pass through the exit.
        :type obj: mudsling.objects.Object
        """
        msg_keys = {
            'actor': obj.ref(),
            'exit': self.ref(),
            'dest': self.dest,
            'room': self.source,
            'source': self.source,
        }
        obj.emit(self.get_message('leave', **msg_keys))
        obj.move_to(self.dest, via=self.ref())
        if obj.has_location and obj.location == self.dest:
            obj.emit(self.get_message('arrive', **msg_keys))

    def exit_list_name(self):
        """
        Return the string to show when the exit is listed.
        """
        aliases = self.aliases
        return "%s {c<{n%s{c>{n" % (self.name,
                                    aliases[0] if aliases else self.name)

    def _call_counterpart(self, fname, *a, **kw):
        c = self.counterpart
        if c is not None:
            return getattr(c, fname)(*a, **kw)


class MatchExit(parsers.MatchObject):
    """
    Parser to match exits in the actor's current room.
    """
    def __init__(self, cls=Exit, err=True, search_for=None, show=False):
        super(MatchExit, self).__init__(cls, err, search_for, show)

    def _match(self, obj, input):
        """
        :param obj: The object from whose perspective the match is attempted.
        :type obj: mudsling.objects.Object
        :param input: The user input being matched against exits.
        :type input: str
        """
        if not obj.isa(LocatedObject):
            raise TypeError("Cannot match exit as non-locatable object.")
        elif not obj.has_location or not obj.location.isa(Room):
            raise ValueError("Cannot match exit when not located in a room.")
        #: @type: Room
        room = obj.location
        return room.match_exits(input)


class room_group_setting(object):
    """
    Descriptor to make room group setting attributes easier to implement.
    """
    __slots__ = ('attr', 'default')

    def __init__(self, attr, default=None):
        self.attr = attr
        self.default = default

    def __get__(self, obj, objtype=None):
        return obj.get_group_setting(self.attr, default=self.default)

    def __set__(self, obj, value):
        setattr(obj, self.attr, value)

    def __delete__(self, obj):
        delattr(obj, self.attr)


class RoomGroup(areas.AreaExportableObject, ConfigurableObject):
    """
    Room groups are used to represent physical groups of rooms, such as a
    building, a floor in a building, or a wing of a building. Groupings are
    arbitrary, and subclasses may be more opinionated.

    Room groups are physical objects that can be located somewhere, and can
    have other objects located within them. A room or other room group is a
    child of a room group by being located directly within it.
    """

    _group_room_class = Room
    _group_exit_class = Exit

    group_room_class = room_group_setting('_group_room_class')
    group_exit_class = room_group_setting('_group_exit_class')

    object_settings = {
        ObjSetting('room_class', type, attr='group_room_class',
                   parser=parsers.ObjClassStaticParser),
        ObjSetting('exit_class', type, attr='group_exit_class',
                   parser=parsers.ObjClassStaticParser)
    }

    def _get_default_class(self, clstype):
        attr = '_group_%s_class' % clstype
        return self.get_group_setting(attr)

    def get_group_setting(self, attr, default=None):
        """
        Resolves a setting based on room group hierarchy, by this priority:
        1. Explicit value on self
        2. First explicit value going up room group hierarchy
        3. Implict value (ie: default from class)
        4. Use provided default if implicit value is None or yields an error

        :param attr: The name of the attribute whose value to seek.
        :type attr: str

        :return: The value discovered in the hierarchy.
        """
        # Defined on self?
        if attr in self.__dict__:
            return getattr(self, attr)
        # Defined somewhere in parent room groups?
        for grp in self.all_parent_room_groups:
            if attr in grp.__dict__:
                return getattr(grp, attr)
        # Use implicit value.
        implicit = getattr(self, attr, None)
        return default if implicit is None else implicit

    def room_desc_tokens(self, room, viewer):
        return {}

    @property
    def has_parent_room_group(self):
        """:rtype: bool"""
        return self.has_location and self.location.isa(RoomGroup)

    @property
    def parent_room_group(self):
        """:rtype: RoomGroup"""
        return self.location if self.has_parent_room_group else None

    @property
    def all_parent_room_groups(self):
        """:rtype: list of RoomGroup"""
        parent = self.parent_room_group
        parents = []
        while parent is not None:
            parents.append(parent)
            parent = parent.parent_room_group
        return parents

    @property
    def child_rooms(self):
        """
        :return: List of area-compatible rooms contained within the room group.
        :rtype: list of Room
        """
        return [r for r in self._contents if r.isa(Room)]

    @property
    def child_room_groups(self):
        """
        :return: List of room groups contained directly within this group.
        :rtype: list of RoomGroup
        """
        return [g for g in self._contents if g.isa(RoomGroup)]

    @property
    def all_room_groups(self):
        """
        :return: List of all room groups contained at any level.
        :rtype: list of RoomGroup
        """
        groups = self.child_room_groups
        groups.extend(itertools.chain.from_iterable(g.all_room_groups
                                                    for g in groups))
        return groups

    @property
    def all_rooms(self):
        """
        :return: List of all rooms contained at any level.
        :rtype: list of Room
        """
        return itertools.chain.from_iterable(g.child_rooms
                                             for g in self.all_room_groups)
