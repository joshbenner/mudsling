import sys
import random

import mudsling.storage

import pathfinder.objects
import pathfinder.conditions


class Battle(mudsling.storage.Persistent):
    """Tracks the rounds and turns in a battle.

    Turn = An individual combatant's opportunity to act during combat.
    Round = A single set of turns, one per combatant.

    :ivar combatants: The combatants participating in the battle.
    :type combatants: list of Combatant

    :ivar active_combatant_offset: The list offset of the combatant who is
        currently taking their turn.
    :type active_combatant_offset: int

    :ivar round: The current round number.
    :type round: int
    """
    combatants = None
    active_combatant_offset = None
    round = 0

    def __init__(self, combatants=()):
        """
        :type combatants: list of Combatant
        """
        # Add them directly, then add them one at a time so they all receive
        # notice of each combatant joining the fray during initialization.
        self.combatants = [c.ref() for c in combatants]
        for combatant in combatants:
            self.add_combatant(combatant, update_initiative=False)
        self.update_initiative()
        self.start_next_round()

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
        except (IndexError, TypeError):
            return None

    @property
    def next_combatant(self):
        if len(self.combatants) < 1:
            return None
        if self.active_combatant_offset > len(self.combatants):
            next_offset = 0
        else:
            next_offset = self.active_combatant_offset + 1
        return self.combatants[next_offset]

    def tell_combatants(self, *parts):
        """Sends text to all combatants in this battle.

        :param parts: The parts of the message in the same format passed to
            :method:`Combatant.tell`.
        :type parts: list
        """
        for combatant in self.combatants:
            combatant.tell(*parts)

    def add_combatant(self, combatant, update_initiative=True):
        """Adds a combatant to the battle.

        :param combatant: The combatant to add.
        :type combatant: Combatant
        :param update_initiative: Whether or not to update initiative.
        :type update_initiative: bool
        """
        combatant = combatant.ref()
        if combatant not in self.combatants:
            self.combatants.append(combatant)
        combatant.battle = self
        self.tell_combatants('{m', combatant, " {gjoins the battle.")
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
        cmp_init = lambda c: c.battle_initiative[2]
        cmp_rand = lambda c: c.battle_initiative[3]
        combatants = sorted(self.combatants, key=cmp_rand)
        combatants = sorted(combatants, key=cmp_init, reverse=True)
        self.combatants = sorted(combatants, key=cmp_roll, reverse=True)
        if current_combatant is not None:
            for i, combatant in enumerate(self.combatants):
                if combatant == current_combatant:
                    self.active_combatant_offset = i
                    break

    def set_active_combatant(self, combatant):
        """Activate a specific combatant.

        :param combatant: The combatant to activate.
        :type combatant: Combatant or mudsling.storage.ObjRef

        :return: The newly-active combatant's round offset, or None.
        :rtype: int or None
        """
        combatant = combatant.ref()
        for i in (i for i, c in enumerate(self.combatants) if c == combatant):
            self.active_combatant_offset = i
            self.tell_combatants("{yIt is now {m", combatant, "'s{y turn.")
            return i
        return None

    def activate_next_combatant(self):
        """Activates the next combatant.

        :return: The newly-active combatant, or None.
        :rtype: Combatant or None
        """
        next_combatant = self.next_combatant
        if next_combatant is not None:
            self.set_active_combatant(next_combatant)
            return self.active_combatant
        return None

    def start_next_round(self):
        self.round += 1
        if self.round == 1:
            for combatant in self.combatants:
                combatant.add_condition(pathfinder.conditions.FlatFooted)
        self.tell_combatants('{yBeginning battle round {c%d{y.' % self.round)
        self.set_active_combatant(self.combatants[0])


class Combatant(pathfinder.objects.PathfinderObject):
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
        result, desc = self.roll('1d20 + initiative', desc=True)
        self.battle_initiative = (result, desc,
                                  self.get_stat('initiative'),
                                  random.randint(0, sys.maxint))
        try:
            self.battle.tell_combatants('{m', self.ref(), "{n rolls {b", desc,
                                        '{n = {c', result,
                                        "{n for initiative.")
        except AttributeError:
            pathfinder.logger.warning("Initiative out of battle for %r", self)
        return self.battle_initiative
