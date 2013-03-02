"""
Rooms and exits.
"""
from mudslingcore.objects import Thing
from mudslingcore.commands import ic


class Room(Thing):

    desc = "A very nondescript room."

    commands = [
        ic.RoomLookCmd
    ]
