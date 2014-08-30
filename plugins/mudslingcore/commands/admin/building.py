"""
Building commands.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling import locks
from mudsling import errors

from mudsling import utils
import mudsling.utils.string

from mudslingcore.topography import Room, Exit, MatchExit


def parse_exit_spec(raw):
    exitNames, sep, returnExitNames = raw.partition('|')
    return (parsers.StringListStaticParser.parse(exitNames),
            parsers.StringListStaticParser.parse(returnExitNames))


# noinspection PyShadowingBuiltins
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

    If you use the /tel switch, you will be moved to the destination room.
    """
    aliases = ('@dig',)
    lock = 'perm(use building commands)'
    syntax = (
        # Parse exitSpec as a single argument rather than including the '|' in
        # the syntax itself so that we can let users quote the entire exit spec
        # in case it contains the string " to " and might break.
        "<exitSpec> to <room>",
        "<newRoomNames>",
    )
    arg_parsers = {
        'exitSpec': parse_exit_spec,
        'newRoomNames': parsers.StringListStaticParser,
    }
    switch_parsers = {
        'tel': parsers.BoolStaticParser,
    }
    switch_defaults = {
        'tel': False,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        if 'exitSpec' in args:  # exit-spec syntax was used, require location.
            if not actor.has_location or not actor.location.is_valid(Room):
                raise self._err("You may only dig exits from within a room.")

        #: @type: L{Room}
        currentRoom = actor.location
        room = self._get_room(actor, args)
        if 'exitSpec' in args:
            exit = self._get_exit(actor, args['exitSpec'][0])
            returnExit = self._get_exit(actor, args['exitSpec'][1])

            if exit:
                exit.source = currentRoom
                exit.dest = room
                currentRoom.add_exit(exit)
                msg = ["{gExit ({m", exit, "{g) created from {c", exit.source,
                       "{g to {c", exit.dest, "{g."]
                actor.msg(msg)

            if returnExit:
                returnExit.source = room
                returnExit.dest = currentRoom
                room.add_exit(returnExit)
                msg = ["{gExit ({m", returnExit, "{g) created from {c",
                       returnExit.source, "{g to {c", returnExit.dest, "{g."]
                actor.msg(msg)

        if self.switches['tel']:
            actor.msg(["{bTeleporting you to {c", room, "{b."])
            actor.move_to(room)

    def _get_room(self, actor, args):
        """
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}

        @raise L{AmbiguousMatch}: When specified room matches multiple rooms.

        @rtype: L{mudslingcore.topography.Room}
        """
        if 'room' in args:
            # Attempt match.
            m = actor.match_object(args['room'], cls=Room)
            if len(m) > 1:
                raise errors.AmbiguousMatch(query=args['room'], matches=m)
            elif len(m) == 1:
                return m[0]  # Single match, that's our room!

        # No matches. Let's create a room!
        if 'room' in args:
            names = parsers.StringListStaticParser.parse(args['room'])
        else:
            names = args['newRoomNames']  # Already parsed.
        return self._create_room(actor, names)

    def _create_room(self, actor, names):
        """
        Create and return a room.

        @type actor: L{mudsling.object.Character}
        @type names: C{list}

        @raise L{CommandInvalid}: When player has invalid room class setting.

        @rtype: L{mudsling.topography.Room}
        """
        roomClass = actor.get_obj_setting('building.room_class')
        if roomClass is not None and issubclass(roomClass, Room):
            room = roomClass.create(names=names, owner=actor)
            actor.msg(["{gCreated {c", room, "{g."])
        else:
            raise self._err("Invalid building.room_class: %r" % roomClass)
        return room

    def _get_exit(self, actor, names):
        """
        Create an exit or return None.

        @type actor: L{mudslingcore.objects.Character}
        @type names: C{list} or C{None}

        @raise L{CommandInvalid}: When player has invalid exit class setting.

        @rtype: L{mudslingcore.topography.Exit}
        """
        if isinstance(names, list):
            exitClass = actor.get_obj_setting('building.exit_class')
            if exitClass is not None and issubclass(exitClass, Exit):
                exit = exitClass.create(names=names, owner=actor)
            else:
                raise self._err("Invalid building.exit_class: %r" % exitClass)
        else:
            exit = None
        return exit


# noinspection PyShadowingBuiltins
class UndigCmd(Command):
    """
    @undig[/both] <exit>

    Removes an exit. Exit can be an exit name, or the numeric offset of the
    exit in the list of exits for the current room.

    If the /both switch is used and true, then any exit in the destination of
    the specified exit which leads back to the exit's source is also removed.
    """
    aliases = ('@undig',)
    lock = 'perm(use building commands)'
    syntax = "<exit>"
    switch_parsers = {
        'both': parsers.BoolStaticParser,
    }
    switch_defaults = {
        'both': False,
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Character}
        @type actor: L{mudslingcore.objects.Character}
        @type args: C{dict}
        """
        #: @type: Room
        room = actor.location
        if not self.game.db.is_valid(room, Room):
            raise errors.CommandError("You must be in a room.")
        exits = room.match_exits(args['exit'])
        if len(exits) > 1:
            msg = "%r can match multiple exits: %s"
            msg = msg % (args['exit'], utils.string.english_list(exits))
            raise errors.AmbiguousMatch(msg=msg)
        elif not exits:
            try:  # Maybe it's an exit offset?
                exitDelta = int(args['exit'])
                if 0 < exitDelta <= len(room.exits):
                    exits = [room.exits[exitDelta - 1]]
            except ValueError:
                raise errors.FailedMatch(query=args['exit'])
        exit = exits[0]
        dest = exit.dest
        msg = actor._format_msg(["{gExit {c", exit,
                                 "{g has been {rdeleted{g."])
        room.remove_exit(exit)
        actor.msg(msg)
        if self.switches['both'] and self.game.db.is_valid(dest, Room):
            others = dest.filter_exits(lambda e: e.dest == room)
            names = utils.string.english_list(
                ['{c' + actor.name_for(x) + '{g' for x in others]
            )
            for o in others:
                dest.remove_exit(o)
            actor.tell("{gExits {rdeleted{g from {m", dest, "{g: ", names)


class RenameExitCmd(Command):
    """
    @rename-exit <exit> to <name>[,<alias>[,...]]

    Rename an exit in the current room.
    """
    aliases = ('@rename-exit', '@rn-exit', '@ren-exit')
    syntax = "<exit> to <newNames>"
    arg_parsers = {
        'exit': MatchExit(search_for='exit', show=True),
        'newNames': parsers.StringListStaticParser,
    }
    lock = locks.all_pass  # Perm check in run().

    def run(self, this, actor, args):
        room = actor.location
        if not self.game.db.is_valid(room, Room):
            raise errors.CommandError("You must be in a room.")
        #: @type: Exit
        exit = args['exit']
        if not exit.allows(actor, 'rename'):
            actor.tell('{yYou are not allowed to rename {c', exit, '{y.')
            return
        names = args['newNames']
        oldName = actor.name_for(exit)
        exit.set_names(names)
        actor.tell('{gExit {y', oldName, '{g renamed to {m', exit,
                   " {g(with aliases: {m", ', '.join(names[1:]), '{g).')
