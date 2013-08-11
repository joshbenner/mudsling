

class Battle(object):
    """
    Tracks the rounds and turns in a battle.

    Turn = An individual combatant's opportunity to act during combat.
    Round = Each combatant gets one turn in a round.
    """

    def __init__(self, combatants=()):
        self.combatants = list(combatants)
        self.current_combatant_offset = 0


class Combatant(object):
    """
    Represents a battle participant.
    """
    battle = None
    battle_initiative = None
