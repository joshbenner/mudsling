import mudsling.utils.string as string_utils

import pathfinder.parsers
import pathfinder.commands
import pathfinder.objects
import pathfinder.combat


class FightCmd(pathfinder.commands.PhysicalCombatCommand):
    """
    fight <character>

    Initiates or joins combat involving the target character.
    """
    aliases = ('fight',)
    syntax = '<character>'
    arg_parsers = {
        'character': pathfinder.parsers.match_combatant
    }
    combat_only = False
    show_emote = False
    action_cost = {}  # Doesn't apply to this command.

    def before_run(self):
        super(FightCmd, self).before_run()
        if self.actor.in_combat:
            raise self._err("You are already fighting.")

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        target = args['character']
        if target.in_combat:
            this.join_battle(target.battle)
        else:
            try:
                this.initiate_battle([target])
            except pathfinder.combat.InvalidBattleLocation as e:
                raise self._err(e.message)


class StandDownCmd(pathfinder.commands.CombatCommand):
    """
    standdown [:<emote>]

    Signal willingness to cease fighting.
    """
    aliases = ('standdown',)
    syntax = '[:<emote>]'
    action_cost = {'standard': 1}
    default_emotes = [
        "remains passive, clearly willing to end the fight.",
    ]

    def run(self, this, actor, args):
        actor.combat_willing = False


class WithdrawCmd(pathfinder.commands.CombatCommand):
    """
    withdraw <exit> [:<emote>]

    Attempts to withdraw from combat.
    """
    aliases = ('withdraw',)
    syntax = '[:<emote>]'
    action_cost = {'standard': 1, 'move': 1}
    default_emotes = [
        'attempts to withdraw from the fight.',
    ]
    # Not implemented yet.


class ApproachCmd(pathfinder.commands.MovementCombatCommand):
    """
    approach <area> [:<emote>]

    Approach an area of the room. Approachable areas include exits, characters,
    and 'open' or 'nothing'.
    """
    aliases = ('approach',)
    syntax = '[<area> [:<emote>]]'
    arg_parsers = {
        'area': pathfinder.parsers.MatchCombatArea()
    }
    action_cost = {'move': 1}
    combat_only = False
    default_emotes = [
        'approaches $area.',
    ]

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        #: :type: pathfinder.objects.Room
        room = actor.location
        position = actor.combat_position or room
        adjacent = room.adjacent_combat_areas(position)
        if 'area' not in args:
            # Empty command, meant to see where combatant can move to.
            areas = string_utils.english_list(["{c%s{n" % a for a in adjacent])
            raise self._err("{nYou can approach: %s" % areas)
        if not self.game.db.is_valid(room, pathfinder.combat.Battleground):
            raise self._err("Unable to maneuver here.")
        destination = args['area']
        if destination not in adjacent:
            destname = actor.combat_position_name(destination)
            posname = actor.combat_position_name(position)
            raise self._err("%s is not adjacent to %s." % (destname, posname))
        try:
            # Stealth move, because command will do its own emote.
            actor.combat_move(destination, stealth=True)
        except pathfinder.combat.InvalidMove as e:
            self._err(e.message)
