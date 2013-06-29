import random

from mudsling.commands import Command
from mudsling import locks
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from dice import Roll

import pathfinder
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
        if self.switches['all']:
            skills = pathfinder.data.registry['skill'].values()
        else:
            skills = this.skills.keys()
        self._show_skill_table(skills, this, actor)

    def _show_skill_table(self, skills, char, actor):
        """
        @type skills: C{list}
        @type char: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        """
        skills = sorted(skills, key=lambda s: s.name)
        from pathfinder import ui
        table = ui.Table([
            ui.Column(''),  # Class skill
            ui.Column(''),  # Untrained
            ui.Column('Skill', align='l'),
            ui.Column('Total'),
            ui.Column('='),
            ui.Column('Trained'),
            ui.Column('+'),
            ui.Column('Ability'),
            ui.Column('+'),
            ui.Column('Misc')
        ])
        class_skills = char.class_skills()
        abil_mods = {}
        abil_mod_str = {}
        for abil in pathfinder.abil_short:
            mod = char.get_stat(abil + ' mod')
            abil_mods[abil] = mod
            abil_mod_str[abil] = pathfinder.format_modifier(mod)
        import time
        a = time.clock()
        d = 0
        for skill in skills:
            abil = skill.ability.lower()
            name = skill.name
            c = time.clock()
            #total = char.get_stat_limits(name)
            total = (0, 0)
            d += (time.clock() - c)
            trained = char.skill_ranks(skill)
            ability = "%s (%s)" % (skill.ability.upper(), abil_mod_str[abil])
            misc_low = total[0] - (trained + abil_mods[abil])
            misc_high = total[1] - (trained + abil_mods[abil])
            misc = pathfinder.format_range(misc_low, misc_high)
            total = pathfinder.format_range(*total)
            untrained = '{y*' if skill.untrained else ''
            class_skill = 'C' if skill in class_skills else ''
            table.add_row([class_skill, untrained, name, total, '', trained,
                           '', ability, '', misc])
        b = (time.clock() - a) * 1000
        actor.msg(ui.report("Skills for %s" % char.name, table,
                            'C = Class skill, * = Use untrained'),
                  flags={'profile': True})
        actor.tell('Skill loop: ', str(b), ' ms')
        actor.tell('get_stat_limits: ', str(d * 1000), ' ms')


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
