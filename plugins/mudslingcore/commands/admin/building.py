"""
Building commands.
"""
from mudsling.commands import Command
from mudsling import parsers
from mudsling import locks
from mudsling import errors
from mudsling.objects import literal_parsers

from mudsling import utils
import mudsling.utils.string

from mudslingcore.rooms import Room, Exit, MatchExit


def parse_exit_spec(raw):
    exitNames, sep, returnExitNames = raw.partition('|')
    return (filter(None, parsers.StringListStaticParser.parse(exitNames)),
            filter(None, parsers.StringListStaticParser.parse(returnExitNames)))


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
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        if 'exitSpec' in args:  # exit-spec syntax was used, require location.
            if not actor.has_location or not actor.location.is_valid(Room):
                raise self._err("You may only dig exits from within a room.")

        #: :type: Room
        currentRoom = actor.location
        room = self._get_room(actor, args)
        if 'exitSpec' in args:
            exit = self._get_exit(actor, args['exitSpec'][0])
            returnExit = self._get_exit(actor, args['exitSpec'][1])

            if exit:
                exit.source = currentRoom
                exit.dest = room
                currentRoom.add_exit(exit, by=actor)
                msg = ["{gExit ({m", exit, "{g) created from {c", exit.source,
                       "{g to {c", exit.dest, "{g."]
                actor.msg(msg)

            if returnExit:
                returnExit.source = room
                returnExit.dest = currentRoom
                room.add_exit(returnExit, by=actor)
                msg = ["{gExit ({m", returnExit, "{g) created from {c",
                       returnExit.source, "{g to {c", returnExit.dest, "{g."]
                actor.msg(msg)

        if self.switches['tel']:
            actor.msg(["{bTeleporting you to {c", room, "{b."])
            actor.move_to(room)

    def _get_room_group(self, actor):
        """:rtype: mudslingcore.rooms.RoomGroup"""
        #: :type: mudslingcore.rooms.Room
        current_room = actor.location
        room_group = None
        if self.game.db.is_valid(current_room, cls=Room):
            room_group = current_room.room_group
        return room_group

    def _get_room(self, actor, args):
        """
        :type actor: mudslingcore.objects.Character
        :type args: dict

        :raise AmbiguousMatch: When specified room matches multiple rooms.

        :rtype: mudslingcore.rooms.Room
        """
        if 'room' in args:
            # Attempt match.
            m = actor.match_object(args['room'], cls=Room)
            if len(m) > 1:
                raise errors.AmbiguousMatch(query=args['room'], matches=m)
            elif len(m) == 1:
                return m[0]  # Single match, that's our room!
            else:
                # Failed match. Usually this means we create. Let's make sure
                # this wasn't a wayward attempt at a literal match.
                if args['room'][:1] in literal_parsers:
                    # They were probably trying to use a literal, and it failed.
                    raise errors.FailedMatch(query=args['room'])

        # No matches. Let's create a room!
        if 'room' in args:
            names = parsers.StringListStaticParser.parse(args['room'])
        else:
            names = args['newRoomNames']  # Already parsed.
        return self._create_room(actor, names)

    def _create_room(self, actor, names):
        """
        Create and return a room.

        :type actor: mudslingcore.objects.Character
        :type names: list

        :raise CommandInvalid: When player has invalid room class setting.

        :rtype: mudslingcore.rooms.Room
        """
        room_group = self._get_room_group(actor)
        if room_group is not None:
            room_class = room_group.group_room_class
        else:
            room_class = actor.get_obj_setting_value('building.room_class')
        if room_class is not None and issubclass(room_class, Room):
            room = room_class.create(names=names, owner=actor)
            actor.tell("{gCreated {c", room, "{g.")
            if room_group is not None:
                room.move_to(room_group)
                actor.tell('{yAdded {c', room, '{y to {m', room_group, '{y.')
        else:
            raise self._err("Invalid building.room_class: %r" % room_class)
        return room

    def _get_exit(self, actor, names):
        """
        Create an exit or return None.

        :type actor: mudslingcore.objects.Character
        :type names: list or None

        :raise CommandInvalid: When player has invalid exit class setting.

        :rtype: mudslingcore.topography.Exit
        """
        if isinstance(names, list) and names:
            room_group = self._get_room_group(actor)
            if room_group is not None:
                exit_class = room_group.group_exit_class
            else:
                exit_class = actor.get_obj_setting_value('building.exit_class')
            if exit_class is not None and issubclass(exit_class, Exit):
                exit = exit_class.create(names=names, owner=actor)
            else:
                raise self._err("Invalid building.exit_class: %r" % exit_class)
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
        :type this: mudslingcore.objects.Character
        :type actor: mudslingcore.objects.Character
        :type args: dict
        """
        #: :type: Room
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
        #: :type: Exit
        exit = args['exit']
        if not exit.allows(actor, 'rename'):
            actor.tell('{yYou are not allowed to rename {c', exit, '{y.')
            return
        names = args['newNames']
        oldName = actor.name_for(exit)
        exit.set_names(names)
        actor.tell('{gExit {y', oldName, '{g renamed to {m', exit,
                   " {g(with aliases: {m", ', '.join(names[1:]), '{g).')
