import sys
import random
from collections import defaultdict

from mudsling.storage import Persistent

from pathfinder.objects import PathfinderObject


class Battle(Persistent):
    """Tracks the rounds and turns in a battle.

    Turn = An individual combatant's opportunity to act during combat.
    Round = A single set of turns, one per combatant.

    :ivar combatants: The combatants participating in the battle.
    :type combatants: list of Combatant

    :ivar active_combatant_offset: The list offset of the combatant who is
        currently taking their turn.
    :type active_combatant_offset: int
    """
    combatants = None
    active_combatant_offset = None

    def __init__(self, combatants=()):
        """
        :type combatants: list of Combatant
        """
        # Add them directly, then add them one at a time so they all receive
        # notice of each combatant joining the fray during initialization.
        self.combatants = list(combatants)
        for combatant in combatants:
            self.add_combatant(combatant, update_initiative=False)
        self.update_initiative()

    @property
    def active(self):
        """Combat is active if there is at least one willing and capable
        combatant and at least two capable combatants.

        :rtype: bool
        """
        capable = [c for c in self.combatants if c.combat_capable]
        willing = [c for c in capable if c.combat_willing]
        return len(willing) > 0 and len(capable) > 1

    @property
    def active_combatant(self):
        """:rtype: Combatant"""
        try:
            return self.combatants[self.active_combatant_offset]
        except IndexError:
            return None

    def tell_combatants(self, *parts):
        for combatant in self.combatants:
            combatant.tell(*parts)

    def add_combatant(self, combatant, update_initiative=True):
        if combatant not in self.combatants:
            self.combatants.append(combatant)
        combatant.battle = self
        self.tell_combatants('{c', combatant, " {yjoins the battle.")
        if update_initiative:
            self.update_initiative()

    def update_initiative(self):
        """Cause any new combatants to roll initiative, and sort the combatants
        into their new combat order.

        The current combatant will remain the current combatant, and new
        combatants will be slotted into where they fit in the initiative order.

        If no combatant was active, the first combatant will be activated.
        """
        current_combatant = self.active_combatant
        for combatant in self.combatants:
            if combatant.battle_initiative is None:
                combatant.roll_initiative()
        cmp_roll = lambda c: c.battle_initiative[0]
        cmp_init = lambda c: c.battle_initiative[1]
        cmp_rand = lambda c: c.battle_initiative[2]
        combatants = sorted(self.combatants, key=cmp_roll)
        combatants = sorted(combatants, key=cmp_init)
        self.combatants = sorted(combatants, key=cmp_rand)
        if current_combatant is not None:
            for i, combatant in enumerate(self.combatants):
                if combatant == current_combatant:
                    self.active_combatant_offset = i
                    break
        else:
            self.set_active_combatant(self.combatants[0])

    def set_active_combatant(self, combatant):
        for i in (i for i, c in enumerate(self.combatants) if c == combatant):
            self.active_combatant_offset = i
            return i
        return None


class Combatant(PathfinderObject):
    """
    Represents a battle participant.

    :ivar battle: The battle the combatant is participating in.
    :type battle: Battle or None

    :ivar battle_initiative: Tuple of initiative roll, initiative bonus, and
        a random tie-breaker value.
    :type battle_initiative: tuple or None

    :ivar combat_willing: If the combatant is willing to fight.
    :type combat_willing: bool

    :ivar combat_capable: If the combatant is capable of fighting.
    :type combat_capable: bool
    """
    battle = None
    battle_initiative = None
    combat_willing = False
    combat_capable = True

    stat_defaults = {
        'initiative': 0,
    }

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

    def roll_initiative(self):
        """Roll initiative for combat.

        :return: Tuple of the rolled initiative value and two tie-breakers.
        :rtype: tuple of int
        """
        self.battle_initiative = (self.roll('1d20 + initiative'),
                                  self.get_stat('initiative'),
                                  random.randint(0, sys.maxint))
        return self.battle_initiative
