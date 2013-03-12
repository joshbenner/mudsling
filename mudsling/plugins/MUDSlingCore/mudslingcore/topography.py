"""
Rooms and exits.
"""
from mudsling.storage import StoredObject
from mudsling.messages import MessagedObject
from mudsling.commands import Command
from mudsling import errors

from mudsling import utils
import mudsling.utils.string

from mudslingcore.objects import DescribableObject, Object
from mudslingcore.commands import ic


class Room(DescribableObject):
    """
    A standard room.

    Features:
    * Looking at things
    * Exits
    """
    desc = "A very nondescript room."

    commands = [
        ic.RoomLookCmd
    ]

    exits = []

    def __init__(self):
        super(Room, self).__init__()
        self.exits = []

    def matchExit(self, search, exactOnly=True):
        return self._match(search, self.exits, exactOnly=exactOnly)

    def handleUnmatchedInputFor(self, actor, raw):
        matches = self.matchExit(raw)
        if len(matches) == 1:
            return ExitCmd(raw, raw, raw, self.game, matches[0], actor)
        elif len(matches) > 1:
            msg = "Which way? {raw!r} matches: {exits}".format(
                raw=raw,
                exits=utils.string.english_list(self.exits)
            )
            raise errors.CommandError(msg)
        else:
            return super(Room, self).handleUnmatchedInput(raw)

    def allowEnter(self, what, exit=None):
        """
        Determines if what may enter this room via the given exit.
        @rtype: bool
        """
        return what.isValid(Object)

    def allowLeave(self, what, exit=None):
        """
        Determines if what may leave this room via the given exit.
        """
        return True

    def enterAllowed(self, what, exit=None):
        """
        Exits call this to ask the room if it has allowed an actual attempt by
        what to transit the exit. This gives the room the opportunity to emit
        messages to the object, itself, etc. apart from the actual evaluation
        of whether the entrance is permitted.
        """
        return self.allowEnter(what, exit=exit)

    def leaveAllowed(self, what, exit=None):
        """
        @see: L{Room.enterStopped}
        """
        return self.allowLeave(what, exit=exit)

    def contentAdded(self, what, previous_location):
        super(Room, self).contentAdded(what, previous_location)
        what.msg(self.seenBy(what))

    def addExit(self, exit):
        if exit.isValid(Exit):
            self.exits.append(exit)

    def descTitle(self, obj):
        return '{y' + super(Room, self).descTitle(obj)

    def asSeenBy(self, obj):
        desc = super(Room, self).asSeenBy(obj)
        contents = self.seenContents(obj)
        exits = self.seenExits(obj)
        if contents:
            desc += '\n\n' + contents
        if exits:
            desc += '\n\n' + exits
        return desc

    def seenContents(self, obj):
        """
        Return the contents of the room as seen by the passed object.
        """
        contents = list(self.contents)
        if obj in contents:
            contents.remove(obj)
        if contents:
            fmt = "{c%s{n"
            if self.game.db.isValid(obj):
                def name(o):
                    return fmt % obj.nameFor(o)
            else:
                def name(o):
                    return fmt % o.name
            names = utils.string.english_list(map(name, contents))
            return "You see %s here." % names
        else:
            return ''

    def seenExits(self, obj):
        if not self.exits:
            return "You do not see any obvious exits."
        names = "{c | {n".join([e.exitListName() for e in self.exits])
        return "{c[{n %s {c]" % names


class Exit(StoredObject, MessagedObject):
    """
    Core exit class.

    Exit subclasses StoredObject to avoid all the functionality that comes
    along with BaseObject. Exits are mostly just data structures decorating
    rooms, but having the API from StoredObject (and thereby, ObjRef) is nice.

    @ivar source: The room where this exit exists.
    @ivar dest: The room to which this exit leads.
    """

    #: @type: L{Room}
    source = None
    #: @type: L{Room}
    dest = None

    messages = {
        'leave': {
            'actor': None,
            '*': "$actor leaves for $exit.",
        },
        'leave_failed': {'actor': "You can't go that way."},
        'arrive': {  # Shown in destination when transiting this exit.
            'actor': None,
            '*': "$actor has arrived."
        },
    }

    def invoke(self, obj):
        """
        Check if obj may pass through this exit, and if so, pass obj through
        this exit.

        @param obj: The object attempting to pass through the exit.
        @type obj: L{Object}
        """
        if self.transitAllowed(obj):
            self._move(obj)
        else:
            obj.emit(self.getMessage('leave_failed',
                                     actor=obj,
                                     exit=self.ref(),
                                     dest=self.dest,
                                     room=self.source,
                                     source=self.source))

    def _invalid_enterAllowed(self, what, exit=None):
        """
        This is used as the enterAllowed call in the event that the destination
        is not a valid Room.
        """
        what.msg("You cannot walk through an exit to nowhere!")
        return False

    def transitAllowed(self, obj):
        """
        Returns True if obj has been allowed to continue on an actual attempt
        to transit the exit. This is not a simple permission check, it is a
        permission check AND resulting in-game effects of the actual attempt to
        transit the exit.

        @see: L{Room.leaveAllowed} and L{Room.enterAllowed}

        @param obj: The object under consideration.
        @type obj: L{Object}
        """
        # Acquire references to the transition attempt result methods from the
        # involved rooms, else placeholder functions.
        leaveAllowed = (obj.location.leaveAllowed
                        if obj.hasLocation and obj.location.isValid(Room)
                        else lambda w, e: True)
        enterAllowed = (self.dest.enterAllowed
                        if self.dest is not None and self.dest.isValid(Room)
                        else self._invalid_enterAllowed)
        return leaveAllowed(obj, self) and enterAllowed(obj, self)

    def _move(self, obj):
        """
        Pass the object through this exit to its destination.
        No permission checks -- just do it!

        @param obj: The object to pass through the exit.
        @type obj: L{Object}
        """
        msgKeys = {
            'actor': obj.ref(),
            'exit': self.ref(),
            'dest': self.dest,
            'room': self.source,
            'source': self.source,
        }
        obj.emit(self.getMessage('leave', **msgKeys))
        obj.moveTo(self.dest)
        if obj.hasLocation and obj.location == self.dest:
            obj.emit(self.getMessage('arrive', **msgKeys))

    def exitListName(self):
        """
        Return the string to show when the exit is listed.
        """
        aliases = self.aliases
        return "%s {c<{n%s{c>{n" % (self.name,
                                    aliases[0] if aliases else self.name)


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
