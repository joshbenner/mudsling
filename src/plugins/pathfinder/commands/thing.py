import mudsling.parsers
import mudsling.errors

import pathfinder.commands
import pathfinder.errors


class WieldCmd(pathfinder.commands.CombatCommand):
    """
    wield <object> [in <hand>[,<hand> ...]] [:<emote>]

    Wields an object.
    """
    aliases = ('wield',)
    syntax = '<object> [in <hands>] [:<emote>]'
    arg_parsers = {
        'object': 'this',
        'hands': mudsling.parsers.StringListStaticParser
    }
    action_cost = {'move': 1}
    combat_only = False
    aggressive = False
    default_emotes = [
        'wields $object.'
    ]

    def run(self, this, actor, args):
        """
        :type this: pathfinder.objects.Thing
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        try:
            actor.wield(this, hands=args.get('hands', None), stealth=True)
        except pathfinder.errors.CannotWield as e:
            self.show_emote = False
            if e.message:
                actor.tell('{rCannot wield ', this, ': %s' % e.message)
            else:
                actor.tell('{rCannot wield ', this, '.')
            raise mudsling.errors.SilentError()


class UnwieldCmd(pathfinder.commands.CombatCommand):
    """
    unwield <object>

    Stop wielding an object.
    """
    aliases = ('unwield',)
    syntax = '<object>'
    arg_parsers = {
        'object': 'this'
    }
    action_cost = {'move': 1}
    combat_only = False
    aggressive = False
    default_emotes = [
        'stops wielding $object.'
    ]

    def run(self, this, actor, args):
        """
        :type this: pathfinder.objects.Thing
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        try:
            actor.unwield(this, stealth=True)
        except pathfinder.errors.NotWielding:
            msg = 'You are not wielding %s.' % actor.name_for(this)
            raise mudsling.errors.CommandInvalid(msg=msg)
