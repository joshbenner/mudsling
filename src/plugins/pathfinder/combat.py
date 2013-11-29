import sys
import random
import inspect
from collections import defaultdict, OrderedDict

from flufl.enum import IntEnum

import mudsling.storage
import mudsling.objects
import mudsling.match
import mudsling.errors
import mudsling.utils.string
import mudsling.utils.units as units

import mudslingcore.topography

from dice import Roll

import pathfinder.objects
import pathfinder.conditions
import pathfinder.errors
import pathfinder.stats
import pathfinder.damage
from pathfinder.events import EventType


class events(object):
    battle_joined = EventType('battle joined')
    battle_left = EventType('battle left')
    turn_started = EventType('combat turn started')
    turn_ended = EventType('combat turn ended')
    round_started = EventType('combat round started')
    round_ended = EventType('combat round ended')
    action_spent = EventType('combat action spent')
    move = EventType('combat move')
    combat_command = EventType('combat command')
    attack_command = EventType('attack command')
    melee_attack_command = EventType('melee attack command')


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

    def __str__(self):
        return 'Combat'

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

    def tell_combatants(self, *parts, **kw):
        """Sends text to all combatants in this battle.

        :param parts: The parts of the message in the same format passed to
            :method:`Combatant.tell`.
        :type parts: list

        :param exclude: Which combatants to exclude from the message.
        :type exclude: list or tuple or set
        """
        exclude = kw.get('exclude', ())
        for combatant in (c for c in self.combatants if c not in exclude):
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

    def remove_combatant(self, combatant, end_battle=False):
        combatant = combatant.ref()
        if combatant in self.combatants:
            if self.active_combatant == combatant and not end_battle:
                self.turn_completed()
            active = self.active_combatant
            self.combatants.remove(combatant)
            if len(self.combatants):
                self.active_combatant_offset = self.combatants.index(active)
            combatant.battle_left(self)
            if not end_battle:
                self.tell_combatants("{m", combatant,
                                     " {yhas left the battle.")

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

    def begin_combatant_turn(self, combatant):
        """Activate a specific combatant.

        :param combatant: The combatant to activate.
        :type combatant: Combatant or mudsling.storage.ObjRef

        :return: The newly-active combatant's round offset, or None.
        :rtype: int or None
        """
        combatant = combatant.ref()
        for i in (i for i, c in enumerate(self.combatants) if c == combatant):
            self.active_combatant_offset = i
            self.active_combatant.begin_battle_turn(round=self.round)
            self.tell_combatants("{yNow taking turn: {m", combatant,
                                 exclude=[combatant])
            return i
        return None

    def activate_next_combatant(self):
        """Activates the next combatant.

        :return: The newly-active combatant, or None.
        :rtype: Combatant or None
        """
        next_combatant = self.next_combatant
        if next_combatant is not None:
            self.begin_combatant_turn(next_combatant)
            return self.active_combatant
        return None

    def start_next_round(self):
        self.round += 1
        self.tell_combatants('{yBeginning battle round {c%d{y.' % self.round)
        for combatant in self.combatants:
            combatant.trigger_event(events.round_started, round=self.round)
        self.begin_combatant_turn(self.combatants[0])

    def end_round(self):
        for combatant in self.combatants:
            combatant.trigger_event(events.round_ended, round=self.round)
        if self.active:
            self.start_next_round()
        else:
            self.end_battle()

    def turn_completed(self):
        """
        Called when current combatant has completed their turn.
        """
        self.tell_combatants('{m', self.active_combatant,
                             '{y ends their turn.')
        self.active_combatant.battle_turn_ended(round=self.round)
        if self.active_combatant_offset == len(self.combatants) - 1:
            self.end_round()
        else:
            self.activate_next_combatant()

    def end_battle(self):
        """
        Called when the battle is no longer active at the end of a round.
        """
        self.tell_combatants("The {rBATTLE{n has {gENDED{n.")
        for combatant in list(self.combatants):
            self.remove_combatant(combatant, end_battle=True)


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

    :ivar combat_actions_spent: A dict of action types and how many are spent.
    :type combat_actions_spent: defaultdict

    :ivar combat_position: What the combatant is "near" in the room.
    :type combat_position: mudsling.objects.Object or None
    """
    battle = None
    battle_initiative = None
    combat_willing = False
    combat_capable = True
    combat_actions_spent = None
    combat_position = None

    # List of bonuses for each attack available to combatant per round.
    #: :type: tuple of int
    attacks = (0,)

    stat_defaults = {
        'initiative': 0,
        'improvised weapon modifier': -4,
    }

    @property
    def in_combat(self):
        """
        :return: Whether or not the combatant is participating in a battle.
        :rtype: bool
        """
        return isinstance(self.battle, Battle)

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
        self.reset_combat_actions()
        self.add_condition(pathfinder.conditions.FlatFooted, source=battle)
        self.trigger_event(events.battle_joined)

    def leave_battle(self):
        if self.battle is not None:
            self.battle.remove_combatant(self.ref())

    def battle_left(self, battle):
        if self.battle == battle:
            self.remove_conditions(source=battle)
            self.battle = None
            self.tell('{gYou have left the battle.')
            self.trigger_event(events.battle_left, battle=battle)

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
            self.battle.tell_combatants('{m', self.ref(), "{n rolls {b", desc,
                                        '{n = {c', result,
                                        "{n for initiative.")
        except AttributeError:
            pathfinder.logger.warning("Initiative out of battle for %r", self)
        return self.battle_initiative

    def roll_attack(self, target, weapon, attack_type, attack_mode,
                    attack_mods=None, improvised=False, stealth=False):
        """
        Perform an attack roll against a target.

        :param target: The target of the attack. Determines target number, etc.
        :type target: pathfinder.objects.PathfinderObject

        :param weapon: The weapon being used to perform the attack. Determines
            the critical threat range, attack bonuses, etc.
        :type weapon: pathfinder.combat.Weapon

        :param attack_type: The type of attack. Determines which bonuses are
            applied to the roll.
        :type attack_type: str

        :param attack_mode: The mode of attack, such as melee or ranged.
        :type attack_mode: str

        :param attack_mods: Additional modifiers to apply to the attack roll.
        :type attack_mods: dict or None

        :param improvised: Whether the attack is improvised.
        :type improvised: bool

        :param stealth: Whether or not to hide the RPG notice output.
        :type stealth: bool

        :return: Tuple of whether the attack hits, and if the attack is a crit.
        :rtype: tuple of bool
        """
        attack_offset = self.spent_combat_actions('attack')
        bab_mod = self.attacks[attack_offset]
        weapon_mod = weapon.get_stat('attack modifier')
        mods = OrderedDict({'attack modifier': '%s attack' % attack_type})
        if bab_mod:
            ordinal = mudsling.match.ordinal_words[attack_offset]
            mods['%s attack' % ordinal] = bab_mod
        if weapon_mod:
            mods['weapon'] = weapon_mod
        if improvised:
            mods['improvised'] = Roll('improvised weapon modifier')
        if attack_mods is not None:
            mods.update(attack_mods)
        vs = ('%s attack' % attack_mode, attack_type)
        target_ac = target.get_stat('ac', vs=vs)
        attack_roll = lambda: self.d20_roll(mods=mods, target_number=target_ac)
        attack = attack_roll()
        desc = attack.success_desc(win='{gHIT', fail='{rMISS', tn_name='AC')
        notice = [self, ' ', ('action', attack_type), ' vs ', target, ': ',
                  ('roll', desc)]
        critical = threat = False
        crit_notice = ()
        if attack.success and attack.natural >= weapon.critical_threat:
            threat = True
            if target.critical_immunity:
                crit_notice = ['  ', ('action', '(critical immunity)')]
            else:
                # Critical threat. Roll against target AC again to confirm.
                confirm = attack_roll()
                confirm_desc = confirm.success_desc(win='{gCONFIRMED',
                                                    fail='{rFAIL',
                                                    tn_name='AC')
                crit_notice = ['  ', ('action', 'Confirm critical: '),
                               ('roll', confirm_desc)]
                if confirm.success:
                    critical = True
        if not stealth:
            self.rpg_notice(*notice)
            if threat:
                self.rpg_notice(*crit_notice)
        return attack.success, critical

    @property
    def combat_action_pool(self):
        return {'move': 1, 'standard': 1, 'attack': len(self.attacks)}

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
        if action_type == 'free':
            return
        if action_type == 'attack':
            if self.remaining_combat_actions('standard'):
                # All attacks in a turn consume a single standard action. We
                # deduct/trigger instead of consume to avoid recursion issues.
                self.deduct_action('standard')
                self.trigger_event(events.action_spent, action_type='standard',
                                   amount=1)
        elif action_type == 'standard':
            # A standard action makes any attacks impossible.
            remaining = self.remaining_combat_actions('attack')
            self.deduct_action('attack', amount=remaining)
        self.deduct_action(action_type, amount=amount)
        self.trigger_event(events.action_spent, action_type=action_type,
                           amount=amount)

    def deduct_action(self, action_type, amount=1):
        """
        Deduction of an action is merely bookkeeping -- no other events are
        triggered off of this.
        """
        self.combat_actions_spent[action_type] += amount

    def begin_battle_turn(self, round=None):
        """
        This is called by the battle when the combatant should begin taking
        its turn.
        """
        if self.has_condition(pathfinder.conditions.FlatFooted):
            self.remove_conditions(pathfinder.conditions.FlatFooted,
                                   source=self.battle)
        self.reset_combat_actions()
        self.tell('{gBegin your turn!')
        self.trigger_event(events.turn_started, round=round,
                           battle=self.battle)

    def end_battle_turn(self):
        """
        This is called when the combatant has completed its turn and the battle
        can progress to the next combatant.
        """
        if self.in_combat and self.battle.active_combatant == self:
            self.battle.turn_completed()

    def battle_turn_ended(self, round=None):
        """
        Called by battle when this combatant's turn has ended.
        """
        self.trigger_event(events.turn_ended, round=round, battle=self.battle)

    def effect_timer_elapse(self, turns=1):
        if not self.in_combat:  # Time flows differently in combat!
            super(Combatant, self).effect_timer_elapse(turns=turns)

    def combat_position_name(self, position):
        if position == self.location:
            name = 'the open'
        elif (isinstance(position, mudsling.storage.ObjRef)
                or isinstance(position, mudsling.objects.Object)):
            name = self.name_for(position)
            if position.isa(mudslingcore.topography.Exit):
                name = "exit to %s" % name
        else:
            name = str(position)
        return name

    def combat_position_desc(self, position):
        if position == self.location:
            return 'in the open'
        else:
            return 'near %s' % self.combat_position_name(position)

    def combat_range_to(self, combatant):
        """
        Determine how far this combatant is from another combatant.

        :param combatant: The other combatant.
        :type combatant: Combatant

        :rtype: int
        """
        if self.has_location and self.location == combatant.location:
            #: :type: Battleground
            here = self.location
            if self.game.db.is_valid(here, Battleground):
                return here.combat_area_distance(self.combat_position,
                                                 combatant.combat_position)
            else:
                return 0
        else:
            return sys.maxint

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
        if prev is None:
            # Broken combat position. Let's try to fix it. We will compromise
            # by doing a move from/to same location, and skip the "you are
            # already there" error.
            prev = where
        elif where == prev and where != self.location:
            # Can approach the open even if you're already there (maneuvering).
            raise InvalidMove("You are already near %s"
                              % self.combat_position_name(where))
        # If another combatant is "near" me, then change their combat position
        # to be my previous position.
        if self.has_location:
            me = self.ref()
            for who in self.location.contents:
                if (who.isa(Combatant)
                        and who.combat_position is not None
                        and who.combat_position == me):
                    who.combat_move(prev, stealth=True)
        self.combat_position = where
        if not stealth:
            fr = self.combat_position_desc(prev)
            if prev == where and where == self.location:
                self.emit(['{m', self.ref(), '{n moves {c', fr, '{n.'])
            else:
                to_ = self.combat_position_desc(where)
                self.emit(['{m', self.ref(), '{n moves from {c', fr,
                           '{n to {c', to_, '{n.'])
        self.trigger_event(events.move, previous=prev)


def attack(attack_group, name=None, improvised=False, default=False, range=0):
    """
    Decorator to esignate a method as an attack callback of a specific type.

    :param attack_group: The type of this attack -- strike, shoot, throw, etc.
    :type attack_group: str
    :param name: The special name (if any) of this attack.
    :type name: str
    :param improvised: Whether or not this attack is improvised.
    :type improvised: bool
    :param default: Whether this attack is the default attack of its type.
    :type default: bool

    :return: A function to wrap a method.
    """
    def decorate(f):
        f.attack_info = AttackInfo(attack_group, name, improvised, default,
                                   range)
        return f
    return decorate


def simple_attack(group, type, mode, name=None, improvised=False,
                  default=False, range=0):
    """
    A function for defining pre-decorated simple attack callbacks.
    """
    def _attack(self, actor, target, **kw):
        return self._standard_attack(actor, target,
                                     attack_type=type,
                                     attack_mode=mode,
                                     **kw)
    decorator = attack(group, name=name, improvised=improvised,
                       default=default, range=range)
    return decorator(_attack)


class AttackInfo(object):
    """
    A simple data class whose instances decorate methods to describe attacks.

    **See:** :func:`attack` decorator
    """
    __slots__ = ('group', 'name', 'improvised', 'default', 'range')

    def __init__(self, group, name=None, improvised=False, default=False,
                 range=0):
        self.group = str(group)
        self.name = (str(name) if name is not None else self.group).lower()
        self.improvised = bool(improvised)
        self.default = bool(default)
        self.range = range

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Attack: %s (%s)' % (self.name, self.group)


class WieldType(IntEnum):
    """
    Objects are designed to be held a certain way. This is a combination of the
    object's weight, design, purpose, etc.
    """
    Light = 0
    OneHanded = 1
    TwoHanded = 2


class Weapon(pathfinder.stats.HasStats):
    """
    A very generic concept of a weapon. This is a superclass of equipment
    weapons (and things that can be weapons in general). This class is a mixin
    to be added to subclasses to enable them to be used as weapons.
    """

    critical_threat = 20
    critical_multiplier = 2
    range_increment = 10 * units.feet
    nonlethal = False

    stat_defaults = {
        'attack modifier': Roll('0'),
        'damage modifier': Roll('0'),
    }
    stat_aliases = {
        'attack': 'attack modifier',
        'damage': 'damage modifier',
    }

    #: The object is designed to be used by creatures of this size.
    user_size = pathfinder.sizes.Medium

    #: The weapon is designed to be held in this manner.
    wield_type = WieldType.OneHanded

    @property
    def name(self):
        return self.__class__.__name__

    @staticmethod
    def __attack_filter(method):
        return inspect.ismethod(method) and 'attack_info' in method.__dict__

    def attacks(self, group=None):
        """
        Get a list of attack types this object is compatible with.

        :param group: Optional filter to limit the returned attack info to
            attacks of a specific group.
        :type group: str

        :return: A list of attacks provided by the object.
        :rtype: list
        """
        callbacks = inspect.getmembers(self, predicate=self.__attack_filter)
        return [getattr(self, f[0]) for f in callbacks
                if group is None or f[1].attack_info.group == group]

    def get_attack(self, group=None, name=None):
        attacks = self.attacks(group)
        if name is None:
            for attack in attacks:
                if attack.attack_info.default:
                    return attack
        else:
            name = name.lower()
            for attack in attacks:
                if name == attack.attack_info.name:
                    return attack
        raise pathfinder.errors.NoSuchAttack()

    def do_attack(self, actor, target, attack_group=None, name=None,
                  nonlethal=None, attack_mods=None):
        """
        Perform a specific attack that this weapon is capable of.

        See :py:meth:`._standard_attack` for a reference attack implementation.

        :param actor: The combatant carrying out the attack.
        :type actor: Combatant

        :param target: The recipient of the attack.
        :type target: pathfinder.objects.PathfinderObject

        :param attack_group: The group of the attack being carried out, such as
            strike, shoot, throw, etc.
        :type attack_group: str

        :param name: Optional specific name of the attack. Useful if a weapon
            has multiple attacks within the specified group. If no name is
            specified, then the default attack in that group is used.
        :type name: str

        :param nonlethal: Whether the attack is intended to deal nonlethal
            damage. Defaults to this weapon's default lethality.
        :type nonlethal: bool

        :param attack_mods: Additional modifiers to the attack roll.
        :type attack_mods: None or dict

        :return: None if the attack misses, else a tuple of Damages.
        :rtype: None or tuple of pathfinder.damage.Damage
        """
        #: See :py:meth:`._standard_attack`
        attack = self.get_attack(attack_group, name)
        if target.isa(Combatant):
            if actor.combat_range_to(target) > attack.attack_info.range:
                raise pathfinder.errors.OutOfAttackRange()
        #: :type: None or tuple of pathfinder.damage.Damage
        damages = attack(actor, target, nonlethal=nonlethal,
                         attack_mods=attack_mods,
                         improvised=attack.attack_info.improvised)
        if damages:
            notice = [('action', '  Damage: '), damages[0]]
            for dmg in damages[1:]:
                notice.extend((', ', dmg))
            actor.rpg_notice(*notice)
            target.take_damage(damages)
        return damages

    def _standard_attack(self, attacker, target, attack_type, attack_mode,
                         nonlethal=None, attack_mods=None, improvised=False):
        """
        A standard attack implementation that can be used in specific attacks.
        This method also serves as the reference attack implementation.

        :param attacker: The object performing the attack.
        :type attacker: Combatant

        :param target: The object being attacked.
        :type target: pathfinder.objects.PathfinderObject

        :param attack_type: The type of attack to perform. This is passed to
            attacker.roll_attack() and is used to determine which stat and
            modifiers to use for the attack roll.
        :type attack_type: str

        :param attack_mode: The manner in which the attack is performed.
            Usually either "melee" or "ranged". This is passed to roll_attack
            and is used to determine if any special-case modifiers apply.
        :type attack_mode: str

        :param nonlethal: Whether the attack is dealing nonlethal damage.
        :type nonlethal: bool

        :param attack_mods: Any additional modifiers to the attack roll.
        :type attack_mods: dict

        :param improvised: Whether the attack is an improvised attack.
        :type improvised: bool

        :returns: None if the attack misses. If the attack hits, then returns
            a tuple of Damage instances.
        :rtype: None or tuple of pathfinder.damage.Damage
        """
        if nonlethal is None:
            nonlethal = self.nonlethal
        if nonlethal != self.nonlethal:
            attack_mods = attack_mods or OrderedDict()
            attack_mods['lethality inversion'] = -4
        hit, crit = attacker.roll_attack(target, weapon=self,
                                         attack_type=attack_type,
                                         attack_mode=attack_mode,
                                         attack_mods=attack_mods,
                                         improvised=improvised)
        if hit:
            return self.roll_damage(attacker, attack_type, crit=crit,
                                    nonlethal=nonlethal, desc=True)
        else:
            return None

    def roll_damage(self, char, attack_type, crit=False, bonus=None,
                    extra=None, nonlethal=None, desc=False):
        """
        Determine how much damage this weapon inflicts this time.

        :param char: The character rolling the damage.
        :param attack_type: The type of attack whose damage to roll.
        :param crit: Whether the attack is a critical hit.
        :param bonus: Additional damage that is multiplied by a critical hit.
        :type bonus: DamageRoll
        :param extra: Extra damage that is NOT multiplied by a critical hit.
        :type extra: DamageRoll
        :param nonlethal: The lethality of the damage. If None, use default.
        :param desc: Whether to generate the damage roll description.

        :rtype: tuple of pathfinder.damage.Damage
        """
        nonlethal = nonlethal if nonlethal is not None else self.nonlethal
        fname = 'roll_%s_damage' % attack_type.replace(' ', '_').lower()
        func = getattr(self, fname)
        damages = func(char, nonlethal=nonlethal, desc=desc)
        if isinstance(damages, pathfinder.damage.Damage):
            damages = [damages]
        else:
            damages = list(damages)
        if bonus:
            damages.append(bonus.roll(char, desc=desc))
        if crit:
            for dmg in damages:
                dmg.points *= self.critical_multiplier
                if desc:
                    dmg.desc = ('(%s) * CRIT(%s)'
                                % (dmg.desc, self.critical_multiplier))
        if extra:
            damages.append(extra.roll(char, desc=desc))
        return tuple(damages)


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

    def combat_area_distance(self, area1, area2):
        """
        Compute the distance (number of moves) between two combat areas.
        """
        here = self.ref()
        if area1 == here and area2 == here:
            # Both in open = 1 step away.
            return 1
        elif area1 == area2:
            return 0
        elif area1.isa(Combatant) and area1.combat_position == area2:
            return 0
        elif area2.isa(Combatant) and area2.combat_position == area1:
            return 0
        elif area1.isa(Combatant) and area2.isa(Combatant):
            return self.combat_area_distance(area1.combat_position,
                                             area2.combat_position)
        elif area1 == here or area2 == here:
            # "The open" is 1 move away from everything. Even two objects in
            # the open must first approach eachother to be at range 0.
            return 1
        else:
            # Every other arrangement is a distance of 2.
            return 2

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
