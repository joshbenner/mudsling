"""
Building commands.
"""
from mudsling.commands import Command
from mudsling import parsers

from mudslingcore.topography import Room, Exit


class DigCmd(Command):
    """
    @dig <exit-spec> to #<roomID>    -- Dig exit to existing room.
    @dig <exit-spec> to <room-names> -- Dig exit to a new room.
    @dig <new-room-name>             -- Create a new room.

    Creates an exit linking to an existing or new room. If no exit is
    specified, then a new room will be created.

    The <exit-spec> may specify the names for both the exit from the current
    room to the new/other room and the names for an exit leading back.

    Example:
        @dig Out,o|In,i to Inner Sanctum
    """
    aliases = ('@dig',)
    syntax = (r"{<exitNames>[|<returnExitNames>]"
              r" to {<room:#\d+>|<roomNames>}|<exitlessRoomNames>}")
    arg_parsers = {
        'exitNames': parsers.StringListParser,
        'returnExitNames': parsers.StringListParser,
        'room': Room,
        'roomNames': parsers.StringListParser,
        'exitlessRoomNames': parsers.StringListParser,
    }
    required_perm = 'use building commands'

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        if args['exitNames'] and (not actor.hasLocation
                                  or not actor.location.isValid(Room)):
            raise self._err("You may only dig exits from a room.")

        #: @type: L{Room}
        currentRoom = actor.location
        room = self._getRoom(actor, args)
        exit = self._getExit(actor, args['exitNames'])
        returnExit = self._getExit(actor, args['returnExitNames'])

        if exit:
            exit.source = currentRoom
            exit.dest = room
            currentRoom.addExit(exit)
            msg = ["{gExit ({c", exit, "{g) created from {c", exit.source,
                   "{g to {c", exit.dest, "{g."]
            actor.msg(msg)

        if returnExit:
            returnExit.source = room
            returnExit.dest = currentRoom
            room.addExit(exit)
            msg = ["{gExit ({c", returnExit, "{g) created from {c",
                   returnExit.source, "{g to {c", returnExit.dest, "{g."]
            actor.msg(msg)

    def _getRoom(self, actor, args):
        """
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        @rtype: L{mudslingcore.topography.Room}
        """
        # First: Are we creating a new room?
        newRoomNames = args['roomNames'] or args['exitlessRoomNames']
        if newRoomNames:
            if not isinstance(newRoomNames, list):
                raise self._err("Invalid room names.")
            name, aliases = newRoomNames[0], newRoomNames[1:]
            roomClass = actor.getObjSetting('building.room_class')
            if roomClass is not None and issubclass(roomClass, Room):
                room = self.game.db.createObject(roomClass, name, aliases)
                actor.msg(["{gCreated {c", room, "{g."])
            else:
                raise self._err("Invalid building.room_class: %r" % roomClass)
        elif args['room']:
            room = args['room']
            if not room.isValid(Room):
                raise self._err("Invalid room.")
        else:
            actor.msg(self.syntaxHelp())
            raise self._err()
        # If we get here, 'room' variable is populated with a room object.
        return room

    def _getExit(self, actor, names):
        """
        @type actor: L{mudslingcore.objects.Character}
        @type names: C{list} or C{None}
        @rtype: L{mudslingcore.topography.Exit}
        """
        if isinstance(names, list):
            name, aliases = names[0], names[1:]
            exitClass = actor.getObjSetting('building.exit_class')
            if exitClass is not None and issubclass(exitClass, Exit):
                exit = self.game.db.createObject(exitClass, name, aliases)
            else:
                raise self._err("Invalid building.exit_class: %r" % exitClass)
        else:
            exit = None
        return exit
