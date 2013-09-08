import mudsling.utils.string as string_utils
import mudsling.commands
import mudsling.locks

import pathfinder.parsers
import pathfinder.commands
import pathfinder.objects
import pathfinder.combat
import pathfinder.characters


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
        if actor.frozen_level < 1:
            raise self._err("You cannot fight until you complete chargen.")
        if (target.isa(pathfinder.characters.Character)
                and target.frozen_level < 1):
            raise self._err("Target has not gone through chargen.")
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
        #: :type: pathfinder.topography.Room
        room = actor.location
        position = actor.combat_position or room
        adjacent = room.adjacent_combat_areas(position)
        if actor in adjacent:
            adjacent.remove(actor)
        if 'area' not in args or args['area'] is None:
            # Empty command, meant to see where combatant can move to.
            areas = string_utils.english_list(["{c%s{n" % a for a in adjacent])
            raise self._err("{nYou can approach: %s" % areas)
        if not self.game.db.is_valid(room, pathfinder.combat.Battleground):
            raise self._err("Unable to maneuver here.")
        destination = args['area']
        if (destination.isa(pathfinder.combat.Combatant)
                and destination.combat_position == actor):
            raise self._err("%s is already near you."
                            % actor.name_for(destination))
        if destination not in adjacent:
            destname = actor.combat_position_name(destination)
            posname = actor.combat_position_name(position)
            raise self._err("%s is not adjacent to %s." % (destname, posname))
        try:
            # Stealth move, because command will do its own emote.
            actor.combat_move(destination, stealth=True)
        except pathfinder.combat.InvalidMove as e:
            raise self._err(e.message)


class WhereAmICmd(mudsling.commands.Command):
    """
    whereami

    Shortcut for *where am I*.
    """
    aliases = ('whereami',)
    lock = mudsling.locks.all_pass

    def run(self, this, actor, args):
        actor.process_input('where am I')


class WhereCmd(mudsling.commands.Command):
    """
    where am I
    where is <combatant>

    Display the combat position of yourself or another combatant.
    """
    aliases = ('where',)
    syntax = (
        'am I',
        'is <combatant>'
    )
    arg_parsers = {
        'combatant': pathfinder.parsers.match_combatant
    }
    lock = mudsling.locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        if 'combatant' in args:
            who = args['combatant']
            actor.tell('{m', args['combatant'], '{n is {c',
                       actor.combat_position_desc(who.combat_position),
                       '{n.')
        else:
            actor.tell('You are {c',
                       actor.combat_position_desc(actor.combat_position),
                       '{n.')


class CombatCmd(mudsling.commands.Command):
    """
    +combat

    Gives you information about the fight you are currently in.
    """
    aliases = ('+combat', '+battle')
    lock = mudsling.locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        #: :type: pathfinder.topography.Room
        room = actor.location
        if not room.isa(pathfinder.combat.Battleground):
            raise self._err("Combat does not work here.")
        battle = room.battle
        if battle is None:
            raise self._err('No combat is taking place here.')
        ui = pathfinder.ui
        table = ui.Table([
            ui.Column('Turn', 4, 'r'),
            ui.Column('Combatant', 20, 'l'),
            ui.Column('Init', 4, 'r'),
            ui.Column('Conditions', '*', 'l', wrap=True)
        ])
        for i, combatant in enumerate(battle.combatants):
            table.add_row([
                '{y=>' if i == battle.active_combatant_offset else '',
                actor.name_for(combatant),
                combatant.battle_initiative[0],
                mudsling.utils.string.english_list(combatant.conditions,
                                                   nothingstr='')
            ])
        actor.msg(ui.report(
            'Combat in %s' % actor.name_for(room),
            table,
            ' {yRound %d' % battle.round)
        )


class ActionsCmd(pathfinder.commands.CombatCommand):
    """
    +actions

    Display the remaining actions during your combat turn.
    """
    aliases = ('+actions', '+turn')
    show_emote = False

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        lines = ['{gAction points remaining:']
        for action_type in actor.combat_action_pool.iterkeys():
            remaining = actor.remaining_combat_actions(action_type)
            total = actor.total_combat_actions(action_type)
            lines.append('  {m%s{n: {y%d / %d' % (action_type.capitalize(),
                                                  remaining,
                                                  total))
        actor.msg('\n'.join(lines))


class EndTurnCmd(pathfinder.commands.CombatCommand):
    """
    endturn

    Ends your combat turn, surrendering any remaining points.
    """
    aliases = ('endturn',)
    show_emote = False

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        actor.end_battle_turn()
