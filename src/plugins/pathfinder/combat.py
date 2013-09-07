import sys
import random
from collections import defaultdict

import mudsling.storage
import mudsling.objects
import mudsling.match
import mudsling.errors
import mudsling.utils.string

import pathfinder.objects
import pathfinder.conditions
import pathfinder.errors


class MoveError(pathfinder.errors.PathfinderError):
    pass


class InvalidMove(MoveError):
    pass


class CannotMove(InvalidMove):
    pass


class InvalidBattleLocation(pathfinder.errors.PathfinderError):
    pass


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
        self.update_initiative(force=True)
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

    def msg_combatants(self, msg, flags=None):
        """
        Call .msg() on all combatants. Useful for sending message templates.
        """
        for combatant in self.combatants:
            combatant.msg(msg, flags=flags)

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
        combatant.battle_joined(self)
        self.tell_combatants('{m', combatant, " {gjoins the battle.")
        if update_initiative:
            self.update_initiative()

    def update_initiative(self, force=False):
        """Cause any new combatants to roll initiative, and sort the combatants
        into their new combat order.

        The current combatant will remain the current combatant, and new
        combatants will be slotted into where they fit in the initiative order.

        If no combatant was active, the first combatant will be activated.
        """
        current_combatant = self.active_combatant
        for combatant in self.combatants:
            if combatant.battle_initiative is None or force:
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
            self.active_combatant.begin_battle_turn()
            self.tell_combatants("{yNow taking turn: {m", combatant)
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

    :ivar combat_action_pool: A dict of action types and how many of them are
        available to the combatant in a turn.
    :type combat_action_pool: defaultdict

    :ivar combat_actions_spent: A dict of action types and how many are spent.
    :type combat_actions_spent: defaultdict

    :ivar combat_position: What the combatant is "near" in the room.
    :type combat_position: mudsling.objects.Object or None
    """
    battle = None
    battle_initiative = None
    combat_willing = False
    combat_capable = True
    combat_action_pool = None
    combat_actions_spent = None
    combat_position = None

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

    @property
    def taking_turn(self):
        return self.in_combat and self.battle.active_combatant == self

    def join_battle(self, battle):
        battle.add_combatant(self.ref())

    def battle_joined(self, battle):
        # Make sure each combatant has a valid combat position.
        if self.combat_position not in self.location.combat_areas():
            self.combat_move(self.location, stealth=True)
        self.battle = battle
        self.combat_action_pool = defaultdict(int, {'move': 1, 'standard': 1})
        self.reset_combat_actions()
        self.add_condition(pathfinder.conditions.FlatFooted, source=battle)

    def initiate_battle(self, other_combatants=()):
        combatants = [self.ref()]
        combatants.extend(other_combatants)
        if (not self.db.is_valid(self.location, Battleground)
                or not self.location.combat_allowed):
            raise InvalidBattleLocation('You cannot fight here.')
        room = self.location.ref()
        battle = None
        for who in [c for c in room.contents if c.isa(Combatant)]:
            if who.in_combat:  # Found existing battle in the room -- join it!
                battle = who.battle
                for combatant in combatants:
                    battle.add_combatant(combatant)
                break
        return battle or Battle(combatants)

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
            inflect = mudsling.utils.string.inflection
            inflect.v
            self.battle.tell_combatants('{m', self.ref(), "{n rolls {b", desc,
                                        '{n = {c', result,
                                        "{n for initiative.")
        except AttributeError:
            pathfinder.logger.warning("Initiative out of battle for %r", self)
        return self.battle_initiative

    def reset_combat_actions(self):
        self.combat_actions_spent = defaultdict(int)

    def total_combat_actions(self, action_type):
        return self.combat_action_pool.get(action_type, 0)

    def spent_combat_actions(self, action_type):
        return self.combat_actions_spent.get(action_type, 0)

    def remaining_combat_actions(self, action_type):
        total = self.total_combat_actions(action_type)
        spent = self.spent_combat_actions(action_type)
        return total - spent

    def consume_action(self, action_type, amount=1):
        self.combat_actions_spent[action_type] += amount

    def begin_battle_turn(self):
        if self.has_condition(pathfinder.conditions.FlatFooted):
            conditions = self.get_condition(pathfinder.conditions.FlatFooted,
                                            source=self.battle)
            if conditions:
                self.remove_condition(conditions[0])
        self.reset_combat_actions()
        self.tell('{gBegin your turn!')

    def combat_position_name(self, position):
        if position == self.location:
            return 'the open'
        if (isinstance(position, mudsling.storage.ObjRef)
                or isinstance(position, mudsling.objects.Object)):
            return self.name_for(position)
        return str(position)

    def combat_position_desc(self, position):
        if position == self.location:
            return 'in the open'
        else:
            return 'near %s' % self.combat_position_name(position)

    def combat_move(self, where, stealth=False):
        """
        The combatant moves from one combat area to another.

        :param where: Where to move to in the room.
        :type where: mudsling.objects.Object

        :param stealth: If true, then the movement does not generate an emit.
        :type stealth: bool

        :raises: CannotMove, InvalidMove
        """
        if self.has_condition(pathfinder.conditions.Immobilized):
            raise CannotMove("You are immobilized")
        prev = self.combat_position
        if where == prev:
            raise InvalidMove("You are already near %s"
                              % self.combat_position_name(where))
        # If another combatant is "near" me, then change their combat position
        # to be my previous position.
        if self.has_location:
            me = self.ref()
            for who in self.location.contents:
                if who.isa(Combatant) and who.combat_position == me:
                    who.combat_move(prev, stealth=True)
        self.combat_position = where
        if not stealth:
            from_ = self.combat_position_desc(prev)
            to_ = self.combat_position_desc(where)
            self.emit([self.ref(), ' moves from ', from_, ' to ', to_, '.'])


class Battleground(mudsling.objects.Object):
    """
    A location where battle can take place.
    """
    combat_allowed = True

    @property
    def battle(self):
        """The battle taking place here, if any.

        :rtype: Battle or None
        """
        for combatant in self.combatants():
            if combatant.in_combat:
                return combatant.battle
        return None

    def combat_areas(self, exclude_self=False):
        """
        Get a list of all combat areas in this room.

        :return: List of all combat areas in room.
        :rtype: list
        """
        areas = [c for c in self.contents if c.isa(Combatant)]
        if not exclude_self:
            areas.append(self.ref())
        return areas

    def adjacent_combat_areas(self, area):
        """
        Get a list of adjacent combat areas. These represent the combat areas
        that a combatant can move into with a single move action.

        Adjacent areas include the 'open' area (the room itself) and any
        combatants in the specified area.

        :param area: The area whose adjacent areas to retriee.

        :return: List of adjacent combat areas.
        :rtype: list

        :raises: ValueError
            When the area is another combatant, and that combatant's position
            is themself (which would result in infinite recursion).
        """
        if self.db.is_valid(area, Combatant):
            # If positioned near another combatant, adjacency is equivalent to
            # the adjacency of that combatant.
            if area.combat_position == area:
                raise ValueError('Combatant %r is adjacent to self' % area)
            return self.adjacent_combat_areas(area.combat_position)
        adjacent = [c for c in self.contents
                    if c.isa(Combatant) and c.combat_position == area]
        if area not in (self, self.ref()):
            # The open area is adjacent to all areas (except itself).
            adjacent.append(self.ref())
        return adjacent

    def match_combat_area(self, input):
        """
        Match a combat area.

        :param input: The string used to match a combat area.
        :type input: str

        :return: A combat area if found.

        :raises: AmbiguousMatch, FailedMatch
        """
        if input in ('open', 'the open', 'the clear', 'nothing'):
            return self.ref()
        matches = mudsling.match.match_objlist(
            input,
            self.combat_areas(exclude_self=True)
        )
        if len(matches) == 1:
            return matches[0].ref()
        else:
            msg = mudsling.match.match_failed(matches, search=input,
                                              search_for='combat area',
                                              show=True)
            if len(matches) > 1:
                raise mudsling.errors.AmbiguousMatch(msg=msg)
            else:
                raise mudsling.errors.FailedMatch(msg=msg)
