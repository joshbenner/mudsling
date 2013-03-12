"""
Building commands.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling.errors import AmbiguousMatch

from mudslingcore.topography import Room, Exit


def parseExitSpec(raw):
    exitNames, sep, returnExitNames = raw.partition('|')
    return (parsers.StringListParser.parse(exitNames),
            parsers.StringListParser.parse(returnExitNames))


class DigCmd(Command):
    """
    @dig <exit-spec> to <exiting-room>    -- Dig exit to existing room.
    @dig <exit-spec> to <new-room-names>  -- Dig exit to a new room.
    @dig <new-room-name>                  -- Create a new room.

    Creates an exit linking to an existing or new room. If no exit is
    specified, then a new room will be created.

    The <exit-spec> may specify the names for both the exit from the current
    room to the new/other room and the names for an exit leading back.

    Example:
        @dig Out,o|In,i to Inner Sanctum
    """
    aliases = ('@dig',)
    required_perm = 'use building commands'
    syntax = (
        # Parse exitSpec as a single argument rather than including the '|' in
        # the syntax itself so that we can let users quote the entire exit spec
        # in case it contains the string " to " and might break.
        "<exitSpec> to <room>",
        "<newRoomNames>",
    )
    arg_parsers = {
        'exitSpec': parseExitSpec,
        'newRoomNames': parsers.StringListParser,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        if 'exitSpec' in args:  # exit-spec syntax was used, require location.
            if not actor.hasLocation or not actor.location.isValid(Room):
                raise self._err("You may only dig exits from within a room.")

        #: @type: L{Room}
        currentRoom = actor.location
        room = self._getRoom(actor, args)
        exit = self._getExit(actor, args['exitSpec'][0])
        returnExit = self._getExit(actor, args['exitSpec'][1])

        if exit:
            exit.source = currentRoom
            exit.dest = room
            currentRoom.addExit(exit)
            msg = ["{gExit ({m", exit, "{g) created from {c", exit.source,
                   "{g to {c", exit.dest, "{g."]
            actor.msg(msg)

        if returnExit:
            returnExit.source = room
            returnExit.dest = currentRoom
            room.addExit(returnExit)
            msg = ["{gExit ({m", returnExit, "{g) created from {c",
                   returnExit.source, "{g to {c", returnExit.dest, "{g."]
            actor.msg(msg)

    def _getRoom(self, actor, args):
        """
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}

        @raise L{AmbiguousMatch}: When specified room matches multiple rooms.

        @rtype: L{mudslingcore.topography.Room}
        """
        if 'room' in args:
            # Attempt match.
            matches = actor.matchObject(args['room'], cls=Room)
            if len(matches) > 1:
                raise AmbiguousMatch(query=args['room'], matches=matches)
            elif len(matches) == 1:
                return matches[0]  # Single match, that's our room!

        # No matches. Let's create a room!
        names = args['room'] if 'room' in args else args['newRoomNames']
        return self._createRoom(actor, parsers.StringListParser.parse(names))

    def _createRoom(self, actor, names):
        """
        Create and return a room.

        @type actor: L{mudsling.object.Character}
        @type names: C{list}

        @raise L{CommandInvalid}: When player has invalid room class setting.

        @rtype: L{mudsling.topography.Room}
        """
        name, aliases = names[0], names[1:]
        roomClass = actor.getObjSetting('building.room_class')
        if roomClass is not None and issubclass(roomClass, Room):
            room = self.game.db.createObject(roomClass, name, aliases)
            actor.msg(["{gCreated {c", room, "{g."])
        else:
            raise self._err("Invalid building.room_class: %r" % roomClass)
        return room

    def _getExit(self, actor, names):
        """
        Create an exit or return None.

        @type actor: L{mudslingcore.objects.Character}
        @type names: C{list} or C{None}

        @raise L{CommandInvalid}: When player has invalid exit class setting.

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
