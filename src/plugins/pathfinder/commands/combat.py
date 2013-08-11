from mudsling.commands import Command

from pathfinder.parsers import MatchCharacter


class FightCmd(Command):
    """
    fight <character>

    Initiates or joins combat involving the target character.
    """
    aliases = ('fight',)
    syntax = '<character>'
    arg_parsers = {
        'character': MatchCharacter()
    }
