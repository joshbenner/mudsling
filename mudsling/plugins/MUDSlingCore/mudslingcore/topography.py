"""
Rooms and exits.
"""
from mudsling.storage import StoredObject

from mudslingcore.objects import Thing
from mudslingcore.commands import ic


class Room(Thing):

    commands = [
        ic.RoomLookCmd
    ]

    desc = "A very nondescript room."

    exits = []

    def __init__(self):
        super(Room, self).__init__()
        self.exits = []


class Exit(StoredObject):
    """
    Exit subclasses StoredObject to avoid all the functionality that comes
    along with BaseObject. Exits are mostly just data structures decorating
    rooms, but having the API from StoredObject (and thereby, ObjRef) is nice.
    """

    source = None
    dest = None
