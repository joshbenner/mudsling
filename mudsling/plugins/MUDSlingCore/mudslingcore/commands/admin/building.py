"""
Building commands.
"""
from mudsling.commands import Command
from mudsling.errors import CommandInvalid

from mudslingcore.topography import Room


class DigCmd(Command):
    """
    @dig <exit-names> to #<roomID>    -- Dig exit to existing room.
    @dig <exit-names> to <room-names> -- Dig exit to a new room.
    @dig <new-room-name>              -- Create a new room.

    Creates an exit linking to an existing or new room. If no exit is
    specified, then a new room will be created.
    """
    aliases = ('@dig',)
    syntax = r"{<exitNames> to {<room:#\d+>|<roomNames>}|<exitlessRoomNames>}"
    arg_parsers = {
        'exitNames': (str.split, ','),
        'room': Room,
        'roomNames': (str.split, ','),
        'exitlessRoomNames': (str.split, ','),
    }
    required_perm = 'use building commands'

    def run(self, this, actor, args):
        room = self._getRoom(actor, args)

    def _getRoom(self, actor, args):
        """
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        @rtype: L{mudslingcore.topography.Room}
        """
        invalid = lambda m=None: CommandInvalid(cmdline=self.raw, msg=m)
        # First: Are we creating a new room?
        newRoomNames = args['roomNames'] or args['exitlessRoomNames']
        if newRoomNames:
            if not isinstance(newRoomNames, list):
                raise invalid("Invalid room names.")
            name, aliases = newRoomNames[0], newRoomNames[1:]
            roomClass = actor.getObjSetting('building.room_class')
            if roomClass is not None and issubclass(roomClass, Room):
                room = self.game.db.createObject(roomClass, name, aliases)
            else:
                raise invalid("Invalid building.room_class: %r" % roomClass)
        elif args['room']:
            room = args['room']
            if not isinstance(room, Room):
                raise invalid("Invalid room.")
        else:
            actor.msg(self.syntaxHelp())
            return None
        # If we get here, 'room' variable is populated with a room object.
        return room
