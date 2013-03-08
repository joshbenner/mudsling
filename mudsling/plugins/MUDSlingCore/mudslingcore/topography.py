"""
Rooms and exits.
"""
from mudsling.storage import StoredObject
from mudsling.messages import MessagedObject
from mudsling.commands import Command
from mudsling import errors
from mudsling.utils import string

from mudslingcore.objects import Thing, Object
from mudslingcore.commands import ic


class Room(Thing):
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

    def handleUnmatchedInput(self, raw):
        matches = self._match(raw, self.exits, exactOnly=True)
        if len(matches) == 1:
            cmd = ExitCmd(raw, raw, raw, self.game, matches[0], self.ref())
        elif len(matches) > 1:
            msg = "Which way? {raw!r} matches: {exits}".format(
                raw=raw,
                exits=string.english_list(self.exits)
            )
            raise errors.CommandError(msg)

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


class Exit(StoredObject, MessagedObject):
    """
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
        leaveAllowed = (obj.location.leaveStopped
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
            'actor': obj,
            'exit': self.ref(),
            'dest': self.dest,
            'room': self.source,
            'source': self.source,
        }
        obj.emit(self.getMessage('leave', msgKeys))
        obj.moveTo(self.dest)
        if obj.hasLocation and obj.location == self.dest:
            obj.emit(self.getMessage('arrive', msgKeys))


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
