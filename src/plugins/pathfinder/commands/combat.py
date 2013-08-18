import mudsling.errors

import pathfinder.parsers
import pathfinder.commands


class FightCmd(pathfinder.commands.PhysicalActionCommand):
    """
    fight <character>

    Initiates or joins combat involving the target character.
    """
    aliases = ('fight',)
    syntax = '<character>'
    arg_parsers = {
        'character': pathfinder.parsers.match_combatant
    }

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.charactesr.Character
        :type args: dict
        """
        target = args['character']
        if this.in_combat:
            raise mudsling.errors.CommandInvalid(
                msg="You are already fighting.")
        if target.in_combat:
            this.join_battle(target.battle)
        else:
            this.initiate_battle([target])
