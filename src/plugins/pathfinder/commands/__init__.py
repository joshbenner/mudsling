import random

import mudsling.locks
import mudsling.commands
import mudsling.utils.string
import mudsling.messages

import pathfinder
import pathfinder.conditions
import pathfinder.errors
import pathfinder.combat


class LevellingCommand(mudsling.commands.Command):
    """
    A command which can only be used while levelling up.
    """

    #: :type: pathfinder.characters.Character
    obj = None
    lock = mudsling.locks.all_pass
    not_levelling_msg = None

    def prepare(self):
        if not self.obj.levelling_up():
            if self.not_levelling_msg is None:
                msg = "{rYou may only use %s while levelling up." % self.cmdstr
            else:
                msg = self.not_levelling_msg
            self.actor.tell(msg)
            return False
        return True


class CombatCommand(mudsling.commands.Command):
    """
    A generic combat command.

    Combat commands will automatically consume their actions. If the command
    does not actually consume its costs (ie: an error, etc), then the command
    should abort by raising an exception.

    :cvar action_cost: Dict of action type keys and their corresponding costs.
    :cvar events: The combat events that are fired after this command.
    :cvar combat_only: Whether the command requires the actor to be in combat.
    :cvar turn_only: Whether the command may only be used in combat during your
        turn.
    :cvar aggressive: Aggressive commands flag the combatant as willing to
        continue fighting.
    """
    #: :type: pathfinder.characters.Character
    actor = None
    action_cost = {}
    events = (pathfinder.combat.events.combat_command,)
    combat_only = True
    turn_only = True
    aggressive = True
    show_emote = True
    default_emotes = [
        "uses a command that needs its default emotes configured."
    ]
    lock = mudsling.locks.all_pass

    @property
    def emote_prefix(self):
        try:
            return self.aliases[0]
        except KeyError:
            return ''

    def consume_actions(self):
        """Consume the action cost of the command from the actor."""
        for action_type, cost in self.action_cost.iteritems():
            self.actor.consume_action(action_type, cost)

    def fire_combat_events(self):
        for event in self.events:
            self.actor.trigger_event(event, cmd=self)

    def check_action_pool(self):
        """Make sure actor has sufficient actions to carry out command."""
        if self.actor.in_combat:
            for action_type, cost in self.action_cost.iteritems():
                if self.actor.remaining_combat_actions(action_type) < cost:
                    return False
        return True

    def before_run(self):
        if self.aggressive:
            self.actor.combat_willing = True
        if self.combat_only and not self.actor.in_combat:
            raise self._err("You are not engaged in combat.")
        elif (self.actor.in_combat and self.turn_only
              and not self.actor.taking_turn):
            raise self._err("You can only do that on your turn.")
        if not self.check_action_pool():
            msg = '{rThe {c%s{r command requires %s.'
            inf = mudsling.utils.string.inflection
            points = mudsling.utils.string.english_list(
                ["{y%d {m%s{r %s" % (c, t, inf.plural_noun('point', c))
                 for t, c in self.action_cost.iteritems()]
            )
            self.actor.tell(msg % (self.aliases[0], points))
            raise self._err("You lack the action points for this command.")

    def after_run(self):
        if self.actor.in_combat:
            self.consume_actions()
            self.fire_combat_events()
        self.display_emote()

    def display_emote(self):
        if self.show_emote:
            emote = self.args.get('emote', None)
            if emote is None:
                raw = random.choice(self.default_emotes)
                emote = mudsling.messages.MessageParser.parse(
                    raw,
                    actor=self.actor.ref(),
                    **self.parsed_args
                )
            if emote:
                prefix = '{m(%s){n ' % self.emote_prefix
                self.actor.emote(emote, prefix=prefix)
            # Prevent double-emotes.
            self.show_emote = False

    def execute(self):
        """
        Override execute to capture some common exceptions.
        """
        try:
            super(CombatCommand, self).execute()
        except pathfinder.errors.OutOfAttackRange as e:
            raise self._err(e.message)


class PhysicalCombatCommand(CombatCommand):
    """
    A command which requires the character to be able to move or act
    physically. These commands will fail if the character is unconscious,
    restrained, etc.
    """
    action_cost = {'standard': 1}
    events = ('combat command', 'physical action')

    def before_run(self):
        super(PhysicalCombatCommand, self).before_run()
        if self.actor.has_condition(pathfinder.conditions.Incapable):
            raise self._err("You are incapacitated!")


class MovementCombatCommand(CombatCommand):
    """
    A command which requires the ability to move and (probably) consumes a
    movement action during a combat turn.
    """
    action_cost = {'move': 1}
    events = ('combat command', 'movement action')

    def before_run(self):
        super(MovementCombatCommand, self).before_run()
        if self.actor.has_condition(pathfinder.conditions.Immobilized):
            raise self._err("You are immobilized!")
