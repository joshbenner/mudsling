from mudsling.objects import BasePlayer, BaseCharacter
from .commands import player as player_commands


class Player(BasePlayer):
    commands = [
        player_commands.EvalCmd
    ]

    def preemptiveCommandMatch(self, input):
        """
        @type input: mudsling.parse.ParsedInput
        """
        if input.raw.startswith(';') and self.hasPerm("eval code"):
            return player_commands.EvalCmd
        return None


class Character(BaseCharacter):
    pass
