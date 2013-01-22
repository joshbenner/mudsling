"""
Rooms and exits.
"""
from mudslingcore.objects import Object
from mudslingcore.commands import ic


class Room(Object):

    desc = "A very nondescript room."

    commands = [
        ic.RoomLookCmd
    ]
