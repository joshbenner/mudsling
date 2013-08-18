import random
import re
import inspect

from mudsling.commands import Command
from mudsling import locks
from mudsling import errors
from mudsling import parsers

from mudsling import utils
import mudsling.utils.string

from mudsling.utils.string import inflection

from mudslingcore.commands import character as core_character_commands
from mudslingcore.genders import genders

from dice import Roll

import ictime.parsers

import pathfinder
from pathfinder import ui
from pathfinder.parsers import AbilityNameStaticParser, RaceStaticParser
from pathfinder.parsers import ClassStaticParser, SkillStaticParser
from pathfinder.parsers import MatchCharacter, FeatStaticParser
import pathfinder.errors as pferr
from pathfinder.commands import LevellingCommand


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
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
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


class AgeCmd(Command):
    """
    +age [<age>]

    Display or set the age of your character.
    """
    aliases = ('+age',)
    syntax = '[<age>]'
    arg_parsers = {
        'age': ictime.parsers.ICDurationStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        age = args['age']
        if age is None:
            actor.tell('{yYou are {c', this.age, '{y old.')
        elif this.frozen_level:
            msg = "You may not set your age after you have finalized."
            raise errors.CommandInvalid(msg=msg)
        else:
            this.age = age
            actor.tell('{gYou are now {c', this.age, "{g old.")


class BornCmd(Command):
    """
    +born [<date>]

    Display or set the birthday of your character.
    """
    aliases = ('+born',)
    syntax = '[<date>]'
    arg_parsers = {
        'date': ictime.parsers.ICDateStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        date = args['date']
        if date is None:
            dob = this.date_of_birth
            actor.tell('{yYou were born on {c', self._date(dob), "{y.")
        elif this.frozen_level:
            msg = "You may not set your birthday after you have finalized."
            raise errors.CommandInvalid(msg=msg)
        else:
            this.date_of_birth = date
            actor.tell('{gYour birthday is now {c', self._date(date), "{g.")

    def _date(self, date):
        return date.format(date.calendar.date_format)


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


class WeightCmd(Command):
    """
    +weight [<weight>]

    Display or specify your character's weight.
    """
    aliases = ('+weight',)
    syntax = '[<weight>]'
    arg_parsers = {
        'weight': parsers.UnitParser(dimensions='mass')
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        @type this: L{pathfinder.characters.Character}
        @type actor: L{pathfinder.characters.Character}
        @type args: C{dict}
        """
        if args['weight'] is None:
            actor.tell('You weigh {y', this.weight, '{n.')
        elif this.frozen_level:
            actor.tell('{rYou may not change your weight after chargen.')
        else:
            this.weight = args['weight']
            actor.tell('You now weigh {y', this.weight, '{n.')


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


class SkillUpCmd(LevellingCommand):
    """
    +skill-up <skill>

    Increase a skill by one rank.
    """
    aliases = ('+skill-up',)
    syntax = '<skill>'
    arg_parsers = {
        'skill': SkillStaticParser
    }
    not_levelling_msg = "{rYou may only gain skill ranks while levelling up."

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


class SkillDownCmd(LevellingCommand):
    """
    +skill-down <skill>

    Decrease a skill by one rank.
    """
    aliases = ('+skill-down',)
    syntax = '<skill>'
    arg_parsers = {
        'skill': SkillStaticParser
    }
    not_levelling_msg = "{rYou may only remove skill ranks while levelling up."

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
            elif not skill.untrained:
                display_name = '{r' + display_name
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


class FeatAddCmd(LevellingCommand):
    """
    +feat-add [<feat>]

    Adds a feat.
    """
    aliases = ('+feat-add',)
    syntax = '[<feat>]'
    arg_parsers = {
        'feat': FeatStaticParser
    }
    not_levelling_msg = "{rYou may only gain feats while levelling up."

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        if args['feat'] is None:
            out = ["{gAvailable feat slot types:"]
            available = this.available_feat_slots().iteritems()
            out.extend([("  {m%s: {y%d" % s) for s in available if s[1] > 0])
            if len(out) > 1:
                actor.msg("\n".join(out))
            else:
                actor.tell("{yNo feat slots available.")
        else:
            feat_class, subtype = args['feat']
            reqs = feat_class.prerequisites(subtype)
            reqs_met, failures = this.check_prerequisites(reqs)
            if not reqs_met:
                name = feat_class.canonical_name(subtype)
                actor.tell_prerequisite_failures(failures, name)
            else:
                try:
                    this.add_feat(feat_class, subtype, source='slot')
                except pferr.PathfinderError as e:
                    raise errors.CommandInvalid(msg=e.message)


class FeatRemoveCmd(LevellingCommand):
    """
    +feat-remove [<feat>]

    Removes a feat from a feat slot.
    """
    aliases = ('+feat-remove', '+feat-rem')
    syntax = '[<feat>]'
    arg_parsers = {
        'feat': FeatStaticParser
    }

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        if args['feat'] is None:
            feats = utils.string.english_list(["{c%s{n" % f
                                               for f in this.level_up_feats],
                                              nothingstr="{rNone")
            actor.tell('{yFeats added during current level-up: ', feats)
        else:
            (feat_class, subtype) = args['feat']
            feat = this.get_feat(feat_class, subtype)
            if feat in this.level_up_feats:
                this.remove_feat(feat, 'slot')
            else:
                n = str(feat_class)
                t = feat_class.feature_type
                if feat is None:
                    actor.tell('{yYou do not have the {c', n, ' {y', t, '.')
                else:
                    actor.tell('{rThe {c', n, ' {r', t, ' cannot be removed.')


class UndoLevelCmd(Command):
    """
    +undo-level

    Undoes any level-up changes that are not yet finalized.
    """
    aliases = ('+undo-level',)
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        if this.frozen_level < this.level:
            this.undo_level()
        else:
            actor.tell('{yYou are not in the process of levelling up!')


class FinalizeCmd(LevellingCommand):
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

    @property
    def not_levelling_msg(self):
        return "{gYou are already finalized at level {c%d{g." % self.obj.level

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        err = []
        if this.race is None:
            err.append("{yYou must select your race! Use {c+race{y.")
        elif this.gender.name.lower() not in this.race.genders:
            err.append('{yYou must choose a valid gender! Use {c+gender{y.')
        if this.date_of_birth is None:
            err.append('{yYou must set your age! Use {c+age {yor {c+born{y.')
        if this.height == 0 * utils.units.m:
            err.append('{yYou must set your height! Use {c+height{y.')
        if this.weight == 0 * utils.units.g:
            err.append('{yYou must set your weight! Use {c+weight{y.')
        if this.level == this.frozen_level:
            err.append('{yYou have not gained any levels to finalized.')
        if this.skill_points > 0:
            msg = '{yYou have {c%d{y unspent skill points! Use {c+skill-up{y.'
            msg %= this.skill_points
            err.append(msg)
        actor.tell('\n'.join(err))
        slots = sum(this.available_feat_slots().itervalues())
        if slots > 0:
            msg = '{yYou have {c%d{y unused feat slots. Use {c+feat-add{y.'
            msg %= slots
            actor.tell(msg)
        if len(err):
            return
        if not self.switches['confirm']:
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
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
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
        fmt = '{abil:<12} ({short}) {{y{score:<5}{{n {mod}'
        lines = ['{cAbility            Score Mod']
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
        hp = ui.conditional_style(char.hp_percent,
                                  styles=self._hp_pct_style,
                                  alternate=str(char.remaining_hp))
        hp_line = ' {cHit Points:{n %s{n / %s' % (hp, char.max_hp)
        if char.temporary_hit_points:
            hp_line += "(%s)" % char.temporary_hit_points
        ac_line = '{cArmor Class:{n %s' % char.armor_class
        init_line = (' {cInitiative:{n %s'
                     % pathfinder.format_mod(char.initiative))
        return hp_line, ac_line, init_line

    def _bottom_table(self, char):
        l = "{{mFort{{n {fort:<2}  (BAB){{n {bab:<+3}  {{yCMB{{n {cmb:<+3}"
        l1 = l.format(
            fort=char.fortitude,
            bab=char.bab,
            cmb=char.cmb
        )
        l = " {{mRef{{n {ref:<2}  {{rMelee{{n {melee:<+3}  {{yCMD{{n {cmd:<+3}"
        l2 = l.format(
            ref=char.reflex,
            melee=char.get_stat('melee attack'),
            cmd=char.cmd
        )
        l3 = "{{mWill{{n {will:<2} {{rRanged{{n {ranged:<+3}".format(
            will=char.will,
            ranged=char.get_stat('ranged attack')
        )
        return l1, l2, l3

    def _vital_table(self, char):
        height = ' '.join(char.height.graduated(strings=True, short=True))
        age = char.age
        return (
            '{c    Race:{n %s' % (char.race if char.race is not None else '?'),
            '{c  Gender:{n %s' % char.gender.name,
            '{c     Age:{n %s' % age.format(age.calendar.age_format),
            '{c  Height:{n %s' % height,
            '{c  Weight:{n %s' % char.weight.short(),
            '{{c      XP:{{n {:,d}'.format(char.xp),
            '{{cNext Lvl:{{n {:,d}'.format(char.next_level_xp)
        )

    def _class_table(self, char):
        lines = ['        {cLevel {y%s' % char.level]
        for class_, lvl in char.classes.iteritems():
            lines.append("{{m{cls:>13} {{n{lvl}".format(cls=class_.name,
                                                        lvl=lvl))
        return lines


class AdminCharsheetCmd(CharsheetCmd):
    """
    @charsheet <character>

    Display the character sheet of another player.
    """
    aliases = ('@charsheet', '@char')
    syntax = '<character>'
    arg_parsers = {
        'character': MatchCharacter()
    }
    lock = locks.Lock('perm(view character sheets)')

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        char = args['character']
        actor.msg(ui.report('Character Sheet: %s' % actor.name_for(char),
                            self._character_sheet(char)))


class FeatsCmd(Command):
    """
    +feats[/all]
    """
    aliases = ('+feats',)
    switches = {
        'all': parsers.BoolStaticParser
    }
    switch_defaults = {
        'all': False
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        if self.switches['all']:
            title = 'All Feats'
            feats = pathfinder.data.all('feat')
        else:
            title = 'Feats for %s' % actor.name_for(actor)
            feats = this.feats
        actor.msg(ui.report(title, self._feat_table(feats)))

    def _feat_table(self, feat_classes):
        """
        :param feat_classes: List of feat classes to include in the table.
        :return: Table instance.
        :rtype: mudsling.utils.string.Table
        """
        table = ui.Table(
            [
                ui.Column('Feat Name', width=30, align='l', wrap=True,
                          cell_formatter=self._format_name),
                ui.Column('Prerequisites', width=30, align='l', wrap=True,
                          cell_formatter=self._format_prerequisites),
                ui.Column('Benefits', width='*', align='l', wrap=True,
                          cell_formatter=self._format_benefits),
            ],
            rowrule=True
        )
        table.add_rows(*sorted(feat_classes, key=lambda f: f.name))
        return table

    def _format_name(self, feat):
        name = str(feat)
        if feat.type != 'general':
            name += " [{m%s{n]" % feat.type
        return name

    def _format_prerequisites(self, feat):
        if inspect.isclass(feat):
            reqs = feat.prerequisites()
        else:
            reqs = feat.prerequisites(feat.subtype)
        return '\n'.join(reqs)

    def _format_benefits(self, feat):
        lines = [feat.description] if len(feat.description) else []
        lines.extend(map(str, feat.modifiers))
        return '\n'.join(lines)


class AdminFeatsCmd(FeatsCmd):
    """
    @feats <character>

    Display the feats for a specific character.
    """
    aliases = ('@feats',)
    syntax = '<character>'
    arg_parsers = {
        'character': MatchCharacter()
    }
    lock = locks.Lock('perm(view feats of others)')
    switches = {}

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        feats = args['character'].feats
        title = "Feats for %s" % actor.name_for(args['character'])
        actor.msg(ui.report(title, self._feat_table(feats)))


class FeatCmd(Command):
    """
    +feat <feat>

    Display information about a single feat.
    """
    aliases = ('+feat',)
    syntax = '<feat>'
    arg_parsers = {
        'feat': FeatStaticParser
    }
    lock = locks.all_pass

    def run(self, this, actor, args):
        """
        :type this: pathfinder.characters.Character
        :type actor: pathfinder.characters.Character
        :type args: dict
        """
        (feat, subtype) = args['feat']
        table = ui.Table(
            [
                ui.Column('Label', width='auto', align='r',
                          cell_formatter=lambda t: "{c%s{y:" % t),
                ui.Column('Value', width='*', align='l', wrap=True),
            ],
            show_header=False,
            frame=False,
            lpad=''
        )
        prerequisites = feat.prerequisites(subtype)
        qualify, misses = this.check_prerequisites(prerequisites)
        met = '{gyou qualify'
        unmet = '{ryou do not qualify'
        reqs = []
        for r in prerequisites:
            reqs.append("%s (%s{n)" % (r, met if r not in misses else unmet))
        if len(reqs) == 0:
            reqs = ['None']
        mods = feat.modifiers
        table.add_rows(
            ['Feat Name', str(feat)],
            ['Description', feat.description],
            ['Requirements', '\n'.join(reqs)]
        )
        if len(mods) > 0:
            table.add_row(['Benefits', '\n'.join(map(str, mods))])
        actor.tell(table)
