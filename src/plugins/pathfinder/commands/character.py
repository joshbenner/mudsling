import random

from mudsling.commands import Command
from mudsling import locks
from mudsling import errors

from dice import Roll

import pathfinder
from pathfinder import inflection
from pathfinder.parsers import AbilityNameStaticParser, RaceStaticParser


class AbilitiesCmd(Command):
    """
    +abilities <best ability>,<next best>,<next>,<next>,<next>,<next>
    +abilities random

    Rank your abilities in order from best to worst.
    """
    aliases = ('+abilities',)
    syntax = (
        '<0>,<1>,<2>,<3>,<4>,<5>',
        'random'
    )
    arg_parsers = dict((str(i), AbilityNameStaticParser) for i in xrange(0, 6))
    lock = locks.all_pass

    roll = Roll('4d6d1')

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if this.finalized:
            msg = "You cannot roll abilities after the character is finalized."
            raise errors.CommandInvalid(msg=msg)
        if '0' in args:
            rand = False
            stats = [args['0'], args['1'], args['2'], args['3'], args['4'],
                     args['5']]
        else:
            rand = True
            stats = pathfinder.abilities
        for abil in pathfinder.abilities:
            if abil not in stats:
                msg = "You must include every ability."
                raise errors.CommandInvalid(msg=msg)
        rolls = sorted([self.roll.eval(desc=True) for _ in xrange(0, 6)],
                       reverse=True,
                       key=lambda i: random.randint(0, 100) if rand else i[0])
        descs = {}
        for i, r in enumerate(rolls):
            stat = stats[i]
            descs[stat] = r[1]
            this.set_stat(stat, r[0])
        actor.msg('{gAbilities rolled:')
        for abil in pathfinder.abilities:
            val = this.get_stat(abil)
            mod = val / 2 - 5
            m = ('+' if mod >= 0 else '') + str(mod)
            v = '{:>2}'.format(val)
            d = descs[abil].replace('+', ' + ').replace('=', ' = ')
            a = '{:>14}'.format(abil.capitalize())
            actor.tell('{m', a, ': {g', v, ' {y', m, ' {n[{c', d, '{n]')

    def syntax_help(self):
        syntax = super(AbilitiesCmd, self).syntax_help()
        syntax += '\n{mAbilities: '
        names = []
        for i, name in enumerate(pathfinder.abilities):
            name = name.capitalize()
            short = pathfinder.abil_short[i].upper()
            names.append('{g' + name + " {n({y" + short + "{n)")
        return syntax + ', '.join(names)


class RaceCmd(Command):
    """
    +race [<race>]

    Select a race, or display the options.
    """
    aliases = ('+race',)
    syntax = '[<race>]'
    arg_parsers = {
        'race': RaceStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        race = args['race']
        if race is None:
            self._show_races(actor)
        else:
            if this.finalized:
                msg = 'You cannot switch races after you finalize!'
                raise errors.CommandInvalid(msg=msg)
            this.set_race(race)
            actor.tell('{gYou are now {c', inflection.a(race.name), '{g.')

    def _show_races(self, actor):
        ui = pathfinder.ui
        table = ui.Table([
            ui.Column('Race', align='r'),
            ui.Column('Abilities', cell_formatter=self._format_abilities,
                      align='l')
        ])
        # Table doesn't do data keys on objects without __dict__!
        for race in pathfinder.data.registry['race'].itervalues():
            table.add_row([race.name, race.ability_modifiers])
        actor.tell(table)

    def _format_abilities(self, mods):
        abils = []
        for abil, val in mods.iteritems():
            i = pathfinder.abilities.index(abil.lower())
            abil = pathfinder.abil_short[i].upper()
            val = pathfinder.format_modifier(val)
            abils.append('{y%s {m%s' % (val, abil))
        return '{n, '.join(abils)


class LevelUpCmd(Command):
    """
    +level-up <class>

    Adds a level of the specified class.
    """
