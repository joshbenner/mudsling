import pathfinder.parsers
import pathfinder.commands


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
    action_cost = {}  # Doesn't apply to this command.

    def before_run(self):
        super(FightCmd, self).before_run()
        if self.actor.in_combat:
            raise self._err("You are already fighting.")

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.charactesr.Character
        :type args: dict
        """
        target = args['character']
        if target.in_combat:
            this.join_battle(target.battle)
        else:
            this.initiate_battle([target])


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
    withdraw [:<emote>]

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
    syntax = '<area> [:<emote>]'
    action_cost = {'move': 1}
    default_emotes = [
        'approaches $area.',
    ]
