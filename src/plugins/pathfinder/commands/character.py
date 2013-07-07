import random
import re

from mudsling.commands import Command
from mudsling import locks
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string
import mudsling.utils.units

from mudsling.utils.string import inflection

from mudslingcore.commands import character as core_character_commands
from mudslingcore.genders import genders

from dice import Roll

import pathfinder
from pathfinder import ui
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
        if this.frozen_level:
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
            if this.frozen_level:
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


class GenderCmd(core_character_commands.GenderCmd):
    """
    +gender [<gender>]

    List current genders or set your gender.
    """
    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if this.race is None:
            actor.tell('{yChoose a race before a gender. Try {c+race')
            return
        valid = sorted([g for n, g in genders.iteritems()
                        if n in this.race.genders],
                       key=lambda g: g.name)
        valid_keys = [g.name.lower() for g in valid]
        show = utils.string.english_list(["{c%s{n" % g.name for g in valid])
        if args['gender'] is None:
            actor.tell('You are a {c', actor.gender.name, '{n.')
            if actor.gender not in valid:
                actor.tell('{rYou must select a valid gender!')
            actor.tell("Possible genders of {m", this.race, "{n: ", show, '.')
        elif this.frozen_level:
            actor.tell('{yYou cannot change your gender after finalizing.')
        elif args['gender'].lower() not in valid_keys:
            actor.tell('{yInvalid gender: {c', args['gender'])
            actor.tell("Possible genders of {m", this.race, "{n: ", show, '.')
        else:
            super(GenderCmd, self).run(this, actor, args)


class HeightCmd(Command):
    """
    +height [<height>]

    Display or specify your character's height.
    """
    aliases = ('+height',)
    syntax = '[<height>]'
    arg_parsers = {
        'height': parsers.UnitParser(dimensions='length')
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if args['height'] is None:
            height = ', '.join(this.dimensions.height.graduated(strings=True))
            actor.tell('You are {y', height, '{n tall.')
        elif this.frozen_level:
            actor.tell('{rYou may not change your height after chargen.')
        else:
            h = args['height']
            this.dimensions = this.dimensions._replace(h=h, units=str(h.units))
            height = ', '.join(this.dimensions.height.graduated(strings=True))
            actor.tell('You are now {y', height, '{n tall.')


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
            this.add_level(class_, ability)


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
    _multiskill_re = re.compile("^(.+) \(.+\)$")

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        self._show_skill_table(self._skills(this), this, actor)

    def _skills(self, char):
        if self.switches['all']:
            return pathfinder.data.registry['skill'].values()
        else:
            return char.skills.keys()

    def _format_range(self, range):
        return pathfinder.format_range(*range, color=True)

    def _format_rank(self, rank):
        return ui.conditional_style(rank, styles=(('>', 0, '{c'),))

    def _show_skill_table(self, skills, char, actor):
        """
        @type skills: C{list}
        @type char: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        """
        skills = sorted(skills, key=lambda s: s.name)
        table = ui.Table([
            ui.Column(''),  # Class skill
            ui.Column(''),  # Untrained
            ui.Column('Skill', align='l'),
            ui.Column('Total', cell_formatter=self._format_range),
            ui.Column('='),
            ui.Column('Trained', cell_formatter=self._format_rank),
            ui.Column('+'),
            ui.Column('Ability'),
            ui.Column('+'),
            ui.Column('Misc', cell_formatter=self._format_range)
        ])
        class_skills = char.class_skills()
        abil_mods = {}
        abil_str = {}
        # Skills with subtypes can make the skill list really long. So, we will
        # only show a subtypeable skill if it is trained. We will at most show
        # one rendition of untrained subtypeable skills.
        multiskills = []
        multiskill_re = self._multiskill_re
        for abil in pathfinder.abil_short:
            mod = char.get_stat(abil + ' mod')
            abil_mods[abil] = mod
            abil_mod_str = pathfinder.format_modifier(mod, color=True)
            abil_str[abil] = "%s (%s{n)" % (abil.upper(), abil_mod_str)
        for skill in skills:
            name = display_name = skill.name
            trained = char.skill_ranks(skill)
            m = multiskill_re.match(name)
            if not trained and m:
                multiskill_name = m.group(1)
                if multiskill_name not in multiskills:
                    display_name = multiskill_name
                    multiskills.append(multiskill_name)
                else:
                    continue
            if trained:
                display_name = '{c' + display_name
            abil = skill.ability.lower()
            total = char.get_stat_limits(name)
            misc_low = total[0] - (trained + abil_mods[abil])
            misc_high = total[1] - (trained + abil_mods[abil])
            misc = (misc_low, misc_high)
            untrained = '{y*' if skill.untrained else ''
            class_skill = '{mC' if skill in class_skills else ''
            table.add_row([class_skill, untrained, display_name, total, '',
                           trained, '', abil_str[abil], '', misc])
        title = "Skills for %s" % actor.name_for(char)
        skill_points = ui.conditional_style(char.skill_points,
                                            styles=(('<', 1, '{r'),))
        footer = '{mC{n = Class skill, {y*{n = Use untrained'
        footer += ' | Available skill points: {y%s' % skill_points
        actor.msg(ui.report(title, table, footer))


class AdminSkillsCmd(SkillsCmd):
    """
    @skills[/all] <character>

    Display someone else's skills.
    """
    aliases = ('@skills',)
    syntax = '<character>'
    arg_parsers = {
        'character': MatchCharacter()
    }
    # Inherits all switch.
    lock = locks.Lock('perm(view skills of others)')

    def run(self, this, actor, args):
        char = args['character']
        self._show_skill_table(self._skills(char), char, actor)


class UndoLevelCmd(Command):
    """
    +undo-level

    Undoes any level-up changes that are not yet finalized.
    """
    aliases = ('+undo-level',)
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if this.frozen_level < this.level:
            this.undo_level()
        else:
            actor.tell('{yYou are not in the process of levelling up!')


class FinalizeCmd(Command):
    """
    +finalize[/confirm]

    Finalize the character, allowing no more changes.
    """
    aliases = ('+finalize',)
    switch_parsers = {
        'confirm': parsers.BoolStaticParser
    }
    switch_defaults = {
        'confirm': False
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if this.frozen_level >= this.level:
            actor.tell('You are already finalized.')
        elif not self.switches['confirm']:
            actor.tell('Once you finalize, you cannot change your character.')
            actor.tell('Are you {ysure{n? If so, type: {c+finalize/confirm')
        else:
            this.finalize_level()


class ResetCharCmd(Command):
    """
    @reset-charsheet[/xp] <character>

    Administrative command to completely reset a character to level 0. If the
    xp switch is used, then the character's accumulated XP is also reset.
    """
    aliases = ('@reset-charsheet',)
    syntax = '<char>'
    arg_parsers = {
        'char': MatchCharacter()
    }
    switch_parsers = {
        'xp': parsers.BoolStaticParser
    }
    switch_defaults = {
        'xp': False
    }
    lock = locks.Lock('perm(reset character sheets)')

    def run(self, this, actor, args):
        char = args['char']
        char.reset_character(wipe_xp=self.switches['xp'])
        if self.switches['xp']:
            actor.tell('{c', char, '{n now has 0 XP.')
        actor.tell('You have reset {c', char, '{n.')


class CharsheetCmd(Command):
    """
    +charsheet

    Display your own character sheet.
    """
    aliases = ('+charsheet', '+char')
    lock = locks.all_pass
    _hp_pct_style = (('>=', 75, '{g'), ('<', 30, '{r'), ('<', 75, '{y'))

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        actor.msg(ui.report('Character Sheet: %s' % actor.name_for(this),
                            self._character_sheet(this)))

    def _character_sheet(self, char):
        ljust = utils.string.ljust  # Handles ANSI.
        abil_table = [ljust(l, 28) for l in self._abil_table(char)]
        mid_table = list(self._top_table(char))
        mid_table.append('')
        mid_table.extend(self._bottom_table(char))
        mid_table = [ljust(l, 27) for l in mid_table]
        vital_table = self._vital_table(char)
        class_table = self._class_table(char)
        tables = (abil_table, mid_table, vital_table, class_table)
        fmt = "{} {{c|{{n {} {{c|{{n {:<20} {}"
        g = lambda t, i: t[i] if i < len(t) else ''
        n = max(len(abil_table), len(class_table))
        lines = [fmt.format(*(g(t, i) for t in tables)) for i in xrange(n)]
        return '\n'.join(lines)

    def _abil_table(self, char):
        fmt = '{abil:<12} ({short}) {score:<5} {mod}'
        lines = ['Ability            Score Mod']
        for abil, short in zip(pathfinder.abilities, pathfinder.abil_short):
            base = char.get_stat_base(abil)
            score = char.get_stat(abil)
            if score != base:
                "{score}{mod:+}".format(score=score, mod=score - base)
            mod = pathfinder.format_mod(char.get_stat(abil + ' mod'),
                                        color=True)
            line = fmt.format(abil=abil.capitalize(),
                              short=short, score=score, mod=mod)
            lines.append(line)
        return lines

    def _top_table(self, char):
        hp = ui.conditional_style(char.hp_percent(),
                                  styles=self._hp_pct_style,
                                  alternate=str(char.remaining_hp()))
        hp_line = ' Hit Points: %s{n / %s' % (hp, char.max_hp)
        if char.temporary_hit_points:
            hp_line += "(%s)" % char.temporary_hit_points
        ac_line = 'Armor Class: %s' % char.armor_class
        init_line = ' Initiative: %s' % pathfinder.format_mod(char.initiative)
        return hp_line, ac_line, init_line

    def _bottom_table(self, char):
        l1 = "Fort {fort:<2}    BAB {bab:<+3}  CMB {cmb:<+3}".format(
            fort=char.fortitude,
            bab=char.bab,
            cmb=char.cmb
        )
        l2 = " Ref {ref:<2}  Melee {melee:<+3}  CMD {cmd:<+3}".format(
            ref=char.reflex,
            melee=char.get_stat('melee attack bonus'),
            cmd=char.cmd
        )
        l3 = "Will {will:<2} Ranged {ranged:<+3}".format(
            will=char.will,
            ranged=char.get_stat('ranged attack bonus')
        )
        return l1, l2, l3

    def _vital_table(self, char):
        height = char.dimensions[2] * utils.units.meter
        feet = int(height.to(utils.units.foot))
        inches = int(height.to(utils.units.inch)) - feet * 12
        pounds = int(char.weight * utils.units.pound)
        return (
            '    Race: %s' % (char.race if char.race is not None else 'none'),
            '  Gender: %s' % char.gender.capitalize(),
            '     Age: %s' % ui.format_interval(char.age, format='%yeary'),
            '  Height: %s\'%s"' % (feet, inches),
            '  Weight: %s lbs' % pounds,
            '      XP: {:,d}'.format(char.xp),
            'Next Lvl: {:,d}'.format(char.next_level_xp)
        )

    def _class_table(self, char):
        lines = ['        Level %s' % char.level]
        for class_, lvl in char.classes.iteritems():
            lines.append("{cls:>13} {lvl}".format(cls=class_.name, lvl=lvl))
        return lines
