import random

from mudsling.commands import Command
from mudsling import locks
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from dice import Roll

import pathfinder
from pathfinder import ui
from pathfinder import inflection
from pathfinder.parsers import AbilityNameStaticParser, RaceStaticParser
from pathfinder.parsers import ClassStaticParser, SkillStaticParser
from pathfinder.parsers import MatchCharacter
import pathfinder.errors as pferr


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
        if not this.str:
            actor.tell('{yYou must first roll your {c+abilities{y!')
            return
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
    +level-up [<class> [+<ability>]]

    Adds a level of the specified class.
    """
    aliases = ('+level-up',)
    syntax = '[<class> [+<ability>]]'
    arg_parsers = {
        'class': ClassStaticParser,
        'ability': AbilityNameStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if not this.get_stat('strength') or this.race is None:
            msg = '{yYou must roll {c+abilities{y and choose a {c+race{y!'
            actor.tell(msg)
            return
        class_ = args['class']
        pending = this.current_xp_level - this.level
        if class_ is None:
            if pending:
                lu = inflection.plural_noun('level-up', pending)
                actor.tell('{yYou have {g', pending, '{y pending ', lu, '.')
                classes = sorted(pathfinder.data.registry['class'].values(),
                                 key=lambda x: x.name)
                classes = ['{m%s{n' % c.name for c in classes]
                classes = utils.string.english_list(classes)
                actor.tell('Available classes: ', classes)
            else:
                actor.tell('{gYou have no pending level-ups.')
            return
        else:
            if not pending:
                actor.tell('{yYou have no pending level-ups.')
                return
            need_ability = ((this.level + 1) % 4 == 0)
            ability = args.get('ability', None)
            if need_ability and ability is None:
                actor.tell('{yYou must indicate the ability to increase.')
                return
            elif not need_ability and ability is not None:
                actor.tell('{yAbilities may be increased every 4th level.')
                return
            if need_ability:
                this.increase_ability(ability)
            this.add_class(class_)


class SkillUpCmd(Command):
    """
    +skill-up <skill>

    Increase a skill by one rank.
    """
    aliases = ('+skill-up',)
    syntax = '<skill>'
    arg_parsers = {
        'skill': SkillStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        try:
            this.add_skill_rank(args['skill'])
        except pferr.SkillError as e:
            actor.tell('{y', e.message)


class SkillDownCmd(Command):
    """
    +skill-down <skill>

    Decrease a skill by one rank.
    """
    aliases = ('+skill-down',)
    syntax = '<skill>'
    arg_parsers = {
        'skill': SkillStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        try:
            this.remove_skill_rank(args['skill'])
        except pferr.SkillError as e:
            actor.tell('{y', e.message)


class SkillsCmd(Command):
    """
    +skills[/all]

    Display your skills.
    """
    aliases = ('+skills',)
    switch_parsers = {
        'all': parsers.BoolStaticParser
    }
    switch_defaults = {
        'all': False
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        skills = this.skills.keys()
        if self.switches['all']:
            for skill in pathfinder.data.registry['skill'].itervalues():
                if skill not in skills:
                    skills.append(skill)
        self._show_skill_table(skills, actor)

    def _show_skill_table(self, skills, actor):
        table = ui.Table([
            ui.Column('Skill'),
            ui.Column('Total'),
            ui.Column('Trained'),
            ui.Column('Ability'),
            ui.Column('Misc')
        ])


class AdminSkillsCmd(SkillsCmd):
    """
    +skills <character>

    Display someone else's skills.
    """
    key = 'admin skills command'  # So it doesn't collide with other +skills.
    aliases = ('+skills',)
    syntax = '<character>'
    arg_parsers = {
        'character': MatchCharacter()
    }
    lock = locks.Lock('perm(view skills of others)')

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        actor.tell('admin skills for ', args['character'])
