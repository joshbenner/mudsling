"""
Rooms and exits.
"""
from mudsling.objects import MessagedObject
from mudsling.objects import Object as LocatedObject
from mudsling.messages import Messages
from mudsling.commands import Command
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from mudslingcore.objects import DescribableObject, Object
from mudslingcore.senses import SensoryMedium


# noinspection PyShadowingBuiltins
class Room(DescribableObject, SensoryMedium):
    """
    A standard room.

    Features:
    * Looking at things
    * Exits
    """
    desc = "A very nondescript room."
    exits = []
    senses = {'hearing', 'vision'}

    def __init__(self, **kwargs):
        super(Room, self).__init__(**kwargs)
        self.exits = []

    def match_exits(self, search, exactOnly=True):
        return self._match(search, self.exits, exactOnly=exactOnly)

    def filter_exits(self, filterfunc):
        """
        Retrieves a list of exits matching the specified filters.
        @param filterfunc: Callback used to filter the list of exits.
        """
        return filter(filterfunc, self.exits)

    def handle_unmatched_input_for(self, actor, raw):
        matches = self.match_exits(raw)
        if len(matches) == 1:
            return ExitCmd(raw, raw, raw, self.game, matches[0], actor)
        elif len(matches) > 1:
            msg = "Which way? {raw!r} matches: {exits}".format(
                raw=raw,
                exits=utils.string.english_list(self.exits)
            )
            raise errors.CommandError(msg)
        else:
            return super(Room, self).handle_unmatched_input(raw)

    def allow_enter(self, what, exit=None):
        """
        Determines if what may enter this room via the given exit.
        @rtype: bool
        """
        return what.is_valid(Object)

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
        @see: L{Room.enterStopped}
        """
        return self.allow_leave(what, exit=exit)

    def add_exit(self, exit):
        if exit.is_valid(Exit):
            self.exits.append(exit)
            if self.db.is_valid(exit.dest, cls=Room):
                exit.dest.entrance_added(exit)

    def entrance_added(self, exit):
        """
        Called when another room adds an exit leading to this room.
        @param exit: The exit that was added.
        """

    def remove_exit(self, exit, delete=True):
        if exit in self.exits:
            self.exits.remove(exit)
            if exit.is_valid(Exit):
                if self.db.is_valid(exit.dest, cls=Room):
                    exit.dest.entrance_removed(exit)
            if exit.is_valid() and delete:
                exit.delete()

    def entrance_removed(self, exit):
        """
        Called when another room removes an exit leading to this room.
        @param exit: The exit that was removed.
        """

    def desc_title(self, obj):
        return '{y' + super(Room, self).desc_title(obj)

    def as_seen_by(self, obj):
        desc = super(Room, self).as_seen_by(obj)
        contents = self.contents_as_seen_by(obj)
        exits = self.exits_as_seen_by(obj)
        if contents:
            desc += '\n\n' + contents
        if exits:
            desc += '\n\n' + exits
        return desc

    def contents_as_seen_by(self, obj):
        """
        Return the contents of the room as seen by the passed object.
        """
        contents = list(self.contents)
        if obj in contents:
            contents.remove(obj)
        if contents:
            fmt = "{c%s{n"
            if self.game.db.is_valid(obj):
                def name(o):
                    return fmt % obj.name_for(o)
            else:
                def name(o):
                    return fmt % o.name
            names = utils.string.english_list(map(name, contents))
            return "You see %s here." % names
        else:
            return ''

    def exits_as_seen_by(self, obj):
        if not self.exits:
            return "You do not see any obvious exits."
        names = "{c | {n".join([e.exit_list_name() for e in self.exits])
        return "{c[{n %s {c]" % names


# noinspection PyShadowingBuiltins
class Exit(MessagedObject):
    """
    Core exit class.

    Transisions an object between two rooms.

    @ivar source: The room where this exit exists.
    @ivar dest: The room to which this exit leads.
    """

    #: @type: L{Room}
    source = None
    #: @type: L{Room}
    dest = None

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

    def invoke(self, obj):
        """
        Check if obj may pass through this exit, and if so, pass obj through
        this exit.

        @param obj: The object attempting to pass through the exit.
        @type obj: L{Object}
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
        This is used as the enter_allowed call in the event that the destination
        is not a valid Room.
        """
        what.msg("You cannot walk through an exit to nowhere!")
        return False

    def transit_allowed(self, obj):
        """
        Returns True if obj has been allowed to continue on an actual attempt
        to transit the exit. This is not a simple permission check, it is a
        permission check AND resulting in-game effects of the actual attempt to
        transit the exit.

        @see: L{Room.leave_allowed} and L{Room.enter_allowed}

        @param obj: The object under consideration.
        @type obj: L{Object}
        """
        # Acquire references to the transition attempt result methods from the
        # involved rooms, else placeholder functions.
        leave_allowed = (obj.location.leave_allowed
                         if obj.has_location and obj.location.is_valid(Room)
                         else lambda w, e: True)
        enter_allowed = (self.dest.enter_allowed
                         if self.dest is not None and self.dest.is_valid(Room)
                         else self._invalid_enter_allowed)
        return leave_allowed(obj, self) and enter_allowed(obj, self)

    def _move(self, obj):
        """
        Pass the object through this exit to its destination.
        No permission checks -- just do it!

        @param obj: The object to pass through the exit.
        @type obj: L{Object}
        """
        msg_keys = {
            'actor': obj.ref(),
            'exit': self.ref(),
            'dest': self.dest,
            'room': self.source,
            'source': self.source,
        }
        obj.emit(self.get_message('leave', **msg_keys))
        obj.move_to(self.dest)
        if obj.has_location and obj.location == self.dest:
            obj.emit(self.get_message('arrive', **msg_keys))

    def exit_list_name(self):
        """
        Return the string to show when the exit is listed.
        """
        aliases = self.aliases
        return "%s {c<{n%s{c>{n" % (self.name,
                                    aliases[0] if aliases else self.name)


# noinspection PyShadowingBuiltins
class ExitCmd(Command):
    """
    <exit-name>

    Proceed through the named exit.
    """
    def run(self, exit, actor, args):
        """
        @param exit: The exit object.
        @type exit: L{Exit}

        @param actor: The object moving through the exit.
        @type actor: L{Object}

        @param args: Unused.
        """
        exit.invoke(actor)


class MatchExit(parsers.MatchObject):
    """
    Parser to match exits in the actor's current room.
    """
    def __init__(self, cls=Exit, err=True, search_for=None, show=False):
        super(MatchExit, self).__init__(cls, err, search_for, show)

    def _match(self, obj, input):
        """
        @param obj: The object from whose perspective the match is attempted.
        @type obj: L{mudsling.objects.Object}
        @param input: The user input being matched against exits.
        @type input: C{str}
        """
        if not obj.isa(LocatedObject):
            raise TypeError("Cannot match exit as non-locatable object.")
        elif not obj.has_location or not obj.location.isa(Room):
            raise ValueError("Cannot match exit when not located in a room.")
        #: @type: Room
        room = obj.location
        return room.match_exits(input)
