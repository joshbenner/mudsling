from mudsling.storage import Persistent

from pathfinder.objects import PathfinderObject


class Battle(Persistent):
    """Tracks the rounds and turns in a battle.

    Turn = An individual combatant's opportunity to act during combat.
    Round = Each combatant gets one turn in a round.
    """

    def __init__(self, combatants=()):
        """
        :type combatants: list of Combatant
        """
        self.combatants = []
        for combatant in combatants:
            self.add_combatant(combatant)
        self.current_combatant_offset = 0

    @property
    def active(self):
        """Combat is active if there is at least one willing and capable
        combatant and at least two capable combatants.

        :rtype: bool
        """
        capable = [c for c in self.combatants if c.combat_capable]
        willing = [c for c in capable if c.combat_willing]
        return len(willing) > 0 and len(capable) > 1

    def tell_combatants(self, *parts):
        for combatant in self.combatants:
            pass

    def add_combatant(self, combatant):
        if combatant in self.combatants:
            return
        combatant.battle = self
        self.combatants.append(combatant)


class Combatant(PathfinderObject):
    """
    Represents a battle participant.
    """
    battle = None
    battle_initiative = None
    combat_willing = False
    combat_capable = True

    @property
    def in_combat(self):
        """
        :return: Whether or not the combatant is participating in a battle.
        :rtype: bool
        """
        return self.battle.active if self.battle is not None else False

    def join_battle(self, battle):
        battle.add_combatant(self.ref())

    def initiate_battle(self, other_combatants=()):
        combatants = [self.ref()]
        combatants.extend(other_combatants)
        battle = Battle(combatants)
        return battle
