import math
import re
import random
from collections import OrderedDict

from mudsling.storage import ObjRef
from mudsling.commands import all_commands
from mudsling.messages import Messages
import mudsling.errors

import mudsling.utils.string as str_utils
import mudsling.utils.sequence as seq_utils

import mudslingcore.objects

import ictime

from dice import Roll

import wearables

import pathfinder
import pathfinder.prerequisites
import pathfinder.features
import pathfinder.events
from pathfinder.events import EventType
import pathfinder.advancement
import pathfinder.combat
import pathfinder.damage
import pathfinder.damage_types
import pathfinder.errors
import pathfinder.equipment
import pathfinder.things
import pathfinder.sizes as sizes


class events(object):
    has_sense = EventType('has sense')
    spoken_languages = EventType('spoken languages')
    allow_def_dex_bonus = EventType('allow defensive dex bonus')
    unarmed_crit_threat = EventType('unarmed critical threat')
    unarmed_crit_multiplier = EventType('unarmed critical multiplier')
    feats = EventType('feats')
    feat_applied = EventType('feat applied')
    feat_removed = EventType('feat removed')


def is_pfchar(obj):
    return (isinstance(obj, Character)
            or (isinstance(obj, ObjRef) and obj.isa(Character)))


class CharacterFeature(pathfinder.features.Feature):
    feature_type = 'character feature'

    def apply_to(self, obj):
        if is_pfchar(obj):
            super(CharacterFeature, self).apply_to(obj)

    def remove_from(self, obj):
        if is_pfchar(obj):
            super(CharacterFeature, self).remove_from(obj)


class UnarmedWeapon(pathfinder.combat.Weapon):
    """
    A special weapon that is instantiated when needed for a specific character.

    The unarmed weapon takes most of its stats from the character it is
    instantiated for.
    """
    nonlethal = True
    wield_type = pathfinder.combat.WieldType.Light
    dmg_roll = pathfinder.damage.DamageRoll
    b = pathfinder.damage_types.Bludgeoning
    damage = {
        sizes.Fine: pathfinder.damage.no_damage,
        sizes.Diminutive: pathfinder.damage.no_damage,
        sizes.Tiny: dmg_roll(1, b),
        sizes.Small: dmg_roll('1d2 + STR mod', b),
        sizes.Medium: dmg_roll('1d3 + STR mod', b),
        sizes.Large: dmg_roll('1d4 + STR mod', b),
        sizes.Huge: dmg_roll('1d8 + STR mod', b),
        sizes.Gargantuan: dmg_roll('2d8 + STR mod', b),
        sizes.Colossal: dmg_roll('4d8 + STR mod', b)
    }
    del dmg_roll, b

    name = 'Unarmed Strike'

    def __init__(self, char):
        """
        :type char: Character
        """
        self.char = char

    @property
    def damage_type(self):
        return self.char.unarmed_damage_type

    @property
    def critical_threat(self):
        return self.char.unarmed_critical_threat

    @property
    def critical_multiplier(self):
        return self.char.unarmed_critical_multiplier

    @property
    def user_size(self):
        return self.char.size_category

    def roll_unarmed_strike_damage(self, char, nonlethal, desc=False):
        return (self.damage[self.user_size].roll(char, nonlethal=nonlethal,
                                                 desc=desc),)

    unarmed_strike = pathfinder.combat.simple_attack(group='strike',
                                                     type='unarmed strike',
                                                     mode='melee',
                                                     default=True)


class Character(mudslingcore.objects.Character,
                wearables.Wearer,
                pathfinder.combat.Combatant):
    """
    A Pathfinder-enabled character/creature/etc.
    """
    messages = Messages({
        'wield': {
            'actor': 'You wield $obj in your $hands.',
            '*': '$actor wields $obj in ${actor.his_her} $hands.'
        },
        'unwield': {
            'actor': 'You stop wielding $obj.',
            '*': '$actor stops wielding $obj.'
        }
    })

    body_regions = ('head', 'face', 'neck', 'chest', 'abdomen', 'back',
                    'left arm', 'right arm', 'left hand', 'right hand',
                    'waist', 'left leg', 'right leg', 'left foot',
                    'right foot')
    #: Mapping of regions that can wield weapons to what they are wielding. The
    #: order is important, as the first item is the primary hand, and the rest
    #: are off-hands.
    #: :type: OrderedDict of pathfinder.objects.Thing
    hands = OrderedDict({
        'right hand': None,
        'left hand': None
    })
    critical_immunity = False
    nonlethal_immunity = False
    hardness = 0
    unarmed_damage_type = 'bludgeoning'
    frozen_level = 0
    xp = 0
    race = None
    levels = []
    # key = level, value = list of (str activity, *value)
    level_history = {}
    favored_class_bonuses = []
    _feats = []
    skills = {}
    skill_points = 0
    level_up_skills = {}
    level_up_feats = []
    feat_slots = {}  # key = type or '*', value = how many
    languages = []
    #: :type: ictime.Date
    date_of_birth = None
    _abil_modifier_stats = (
        'strength modifier',
        'dexterity modifier',
        'constitution modifier',
        'wisdom modifier',
        'intelligence modifier',
        'charisma modifier'
    )
    _abil_bonus_stats = (
        'strength bonus',
        'dexterity bonus',
        'constitution bonus',
        'wisdom bonus',
        'intelligence bonus',
        'charisma bonus',
    )
    # If it can be modifier separately, it is NOT an alias!
    stat_aliases = {
        'str': 'strength',     'str mod': 'strength modifier',
        'dex': 'dexterity',    'dex mod': 'dexterity modifier',
        'con': 'constitution', 'con mod': 'constitution modifier',
        'wis': 'wisdom',       'wis mod': 'wisdom modifier',
        'int': 'intelligence', 'int mod': 'intelligence modifier',
        'cha': 'charisma',     'cha mod': 'charisma modifier',
        'str modifier': 'strength modifier',
        'dex modifier': 'dexterity modifier',
        'con modifier': 'constitution modifier',
        'wis modifier': 'wisdom modifier',
        'int modifier': 'intelligence modifier',
        'cha modifier': 'charisma modifier',
        'strength mod': 'strength modifier',
        'dexterity mod': 'dexterity modifier',
        'constitution mod': 'constitution modifier',
        'wisdom mod': 'wisdom modifier',
        'intelligence mod': 'intelligence modifier',
        'charisma mod': 'charisma modifier',

        'str bonus': 'strength bonus',
        'dex bonus': 'dexterity bonus',
        'con bonus': 'constitution bonus',
        'wis bonus': 'wisdom bonus',
        'int bonus': 'intelligence bonus',
        'cha bonus': 'charisma bonus',

        'lvl': 'level',
        'hd': 'hit dice',
        'bab': 'base attack bonus',
        'ac': 'armor class',
        'size mod': 'size modifier',
        'special size mod': 'special size modifier',

        'fort': 'fortitude', 'ref': 'reflex',
        'cmb': 'combat maneuver bonus',
        'cmd': 'combat maneuver defense',

        'all saving throws': 'all saves',
        'saving throws': 'all saves',

        # The aliases keep attack type stat resolution consistent.
        'unarmed attack': 'unarmed strike',
        'lethal unarmed attack': 'lethal unarmed strike',
        'unarmed strike attack': 'unarmed strike',
        'lethal unarmed strike attack': 'lethal unarmed strike',
    }
    stat_defaults = {
        'strength': 0,
        'dexterity': 0,
        'constitution': 0,
        'wisdom': 0,
        'intelligence': 0,
        'charisma': 0,

        # The ability checks can be modified separately from the base stat or
        # their modifiers.
        'strength check': Roll('strength modifier'),
        'dexterity check': Roll('dexterity modifier'),
        'constitution check': Roll('constitution modifier'),
        'wisdom check': Roll('wisdom modifier'),
        'intelligence check': Roll('intelligence modifier'),
        'charisma check': Roll('charisma modifier'),

        'level': 0,

        'initiative': Roll('dexterity modifier'),
        'shield bonus': 0,
        'armor bonus': 0,
        'armor enhancement bonus': 0,
        'range increment modifier': -2,
        'shoot into melee modifier': -4,
        'improvised weapon modifier': -4,
        'two weapon primary hand modifier': -4,
        'two weapon off hand modifier': -8,
        'melee damage modifier': Roll('strength modifier'),
        'primary melee damage bonus': Roll('melee damage modifier'),
        'off hand melee damage bonus': Roll('trunc(melee damage modifier/2)'),

        'armor dex limit': 99,  # todo: Retrieve this from armor.
        'armor class': Roll('10 + armor bonus + shield bonus'
                            ' + defensive dex mod + size modifier'),
        'armor class against melee attacks': 0,
        'armor class against ranged attacks': 0,

        'combat maneuver bonus': Roll('BAB + STR mod + special size mod'),
        'combat maneuver defense': Roll('10 + BAB + STR mod'
                                        '+ defensive dex mod'
                                        '+ special size mod'),

        # These are the fundamental attack bonuses. Actual attacks will use the
        # rolls specified below.
        'base attack bonus': 0,
        'melee attack': Roll('BAB + STR mod + size mod'),
        'ranged attack': Roll('BAB + DEX mod + size mod'),
        'melee touch attack': Roll('melee attack'),
        'ranged touch attack': Roll('ranged attack'),
        'unarmed strike': Roll('melee attack'),
        'lethal unarmed strike': Roll(
            'unarmed strike + lethality inversion'),
        'lethality inversion': -4,
    }
    # Map attributes to stats.
    stat_attributes = {
        'level': 'level',
        'strength': 'strength',
        'constitution': 'constitution',
        'dexterity': 'dexterity',
        'wisdom': 'wisdom',
        'intelligence': 'intelligence',
        'charisma': 'charisma',
        'str': 'strength', 'con': 'constitution', 'dex': 'dexterity',
        'wis': 'wisdom', 'int': 'intelligence', 'cha': 'charisma',
        'strength_mod': 'strength modifier',
        'constitution_mod': 'constitution modifier',
        'dexterity_mod': 'dexterity modifier',
        'wisdom_mod': 'wisdom modifier',
        'intelligence_mod': 'intelligence modifier',
        'charisma_mod': 'charisma modifier',
        'str_mod': 'strength modifier',
        'con_mod': 'constitution modifier',
        'dex_mod': 'dexterity modifier',
        'wis_mod': 'wisdom modifier',
        'int_mod': 'intelligence modifier',
        'cha_mod': 'charisma modifier',
        'armor_class': 'armor class',
        'initiative': 'initiative',
        'base_attack_bonus': 'base attack bonus',
        'bab': 'base attack bonus',
        'fortitude': 'fortitude', 'reflex': 'reflex', 'will': 'will',
        'size_modifier': 'size modifier',
        'size_mod': 'size modifier',
        'special_size_modifier': 'special size modifier',
        'special_size_mod': 'special size modifier',
        'combat_maneuver_bonus': 'combat maneuver bonus',
        'cmb': 'combat maneuver bonus',
        'combat_maneuver_defense': 'combat maneuver defense',
        'cmd': 'combat maneuver defense',
    }

    # These are used to resolve stats to their canonical form.
    _skill_check_re = re.compile('(.*)(?: +(check|roll)s?)', re.I)
    _save_re = re.compile(
        '(Fort(?:itude)?|Ref(?:lex)?|Will)( +(save|check)s?)', re.I)

    # Used to identify class level stats for isolating base stat value.
    _class_lvl_re = re.compile('(.*) +levels?', re.I)

    def describe_to(self, viewer):
        desc = super(Character, self).describe_to(viewer)
        wielding = self.wielded_weapons
        if wielding:
            desc += '\nWielding:'
            for weapon in wielding:
                hands = str_utils.english_list(self.hands_wielding(weapon))
                desc += '\n  {y' + viewer.name_for(weapon)
                desc += ' {nin ' + hands
        return desc

    def has_sense(self, sense):
        """Some features may prevent hearing or seeing."""
        has = super(Character, self).has_sense(sense)
        if has:
            event = self.trigger_event(events.has_sense, sense=sense)
            has = False not in event.responses.itervalues()
        return has

    @property
    def age(self):
        """
        :rtype: ictime.Duration
        """
        if self.date_of_birth is None:
            return ictime.Duration(0)
        else:
            today = self.date_of_birth.calendar.today()
            return today - self.date_of_birth

    @age.setter
    def age(self, age):
        if isinstance(age, ictime.Duration):
            today = age.calendar.today()
            self.date_of_birth = today - age
        else:
            raise TypeError("Character age must be of type ictime.Duration")

    @property
    def height(self):
        return self.dimensions.height

    _dependent_data = dict(pathfinder.combat.Combatant._dependent_data)
    _dependent_data['feats'] = {
        'process': '_process_features',
        'start': lambda o: list(o._feats),
        'cache': '__feats'
    }
    _dependent_data['static feat providers'] = {
        'process': '_process_features',
        'start': lambda o: seq_utils.flatten((o.classes.keys(), o.race))
    }

    def _process_effects(self, effects, data):
        super(Character, self)._process_effects(effects, data)
        event = pathfinder.events.Event(events.feats)
        event.feats = []
        for provider in effects:
            provider.respond_to_event(event, None)
        data['feats'].extend(event.feats)

    @property
    def feats(self):
        """:rtype: list of pathfinder.feats.Feat"""
        if '__feats' in self._stat_cache:
            return list(self._stat_cache['__feats'])
        self._build_dependent_data()
        return self.feats

    @property
    def features(self):
        features = super(Character, self).features
        if self.race is not None:
            features.append(self.race)
        features.extend(self.classes.iterkeys())
        features.extend(self.feats)

        return features

    @property
    def classes(self):
        if '__classes' in self._stat_cache:
            return dict(self._stat_cache['__classes'])
        classes = {}
        for lvl in self.levels:
            if lvl not in classes:
                classes[lvl] = 1
            else:
                classes[lvl] += 1
        self._check_attr('_stat_cache', {})
        self._stat_cache['__classes'] = classes
        return dict(classes)

    @property
    def favored_classes(self):
        return (self.levels[0],) if self.levels else ()

    @property
    def unused_favored_class_bonuses(self):
        """
        Return the number of unused favored class bonuses.
        @rtype: C{int}
        """
        bonuses = 0
        favored = self.favored_classes
        for cls in self.levels:
            if cls in favored:
                bonuses += 1
        return bonuses - len(self.favored_class_bonuses)

    @property
    def can_use_defensive_dex_bonus(self):
        event = pathfinder.events.Event(events.allow_def_dex_bonus)
        return False not in self.trigger_event(event).responses.values()

    def trigger_event(self, event, **kw):
        event = super(Character, self).trigger_event(event, **kw)
        if event.name == 'alter roll' and 'attack roll' in kw['tags']:
            mods = self.get_stat_modifiers('all attacks')
            raise NotImplemented
        elif event.type in (events.feat_applied, events.feat_removed):
            self.clear_stat_cache()
        return event

    def _set_damage_conditions(self, prev_hp, prev_nl_damage):
        """
        Set various conditions based on current hit points as well as their
        previous values.

        :param prev_hp: Previous hit points.
        :param prev_nl_damage: Previous nonlethal damage.
        """
        hp = self.remaining_hp
        nl_damage = self.nonlethal_damage
        hp_conditions = self.get_conditions(source='damage')
        current_conditions = set([c.name.lower() for c in hp_conditions])
        new_conditions = set()
        if 'unconscious' in current_conditions:
            # Stay unconscious unless specifically removed.
            new_conditions.add('unconscious')

        # Conditions based on nonlethal damage.
        if nl_damage == hp and prev_nl_damage != hp:
            new_conditions.add('staggered')
        elif nl_damage > hp and prev_nl_damage <= prev_hp:
            new_conditions.add('unconscious')
        elif (nl_damage < hp and prev_nl_damage >= prev_hp
                and 'unconscious' in new_conditions):
            new_conditions.remove('unconscious')

        # Conditions based on hit points.
        if hp <= -self.constitution:
            new_conditions.add('dead')
        elif hp == 0:
            new_conditions.add('disabled')
        elif hp < 0:
            # Note: If they are stable and take damage, they resume dying.
            new_conditions.add('dying')
            if prev_hp >= 0:  # Go unconsciou when they first fall below.
                new_conditions.add('unconscious')
        elif hp >= 0 > prev_hp and 'unconcious' in new_conditions:
            new_conditions.remove('unconscious')

        # Apply changes.
        for condition in hp_conditions:
            if condition.name.lower() not in new_conditions:
                self.remove_condition(condition)
        for condition in new_conditions:
            if condition not in current_conditions:
                self.add_condition(condition, source='damage')

    def attempt_to_stabilize(self):
        if not self.has_condition('dying', source='damage'):
            # No need to attempt to stabilize.
            return None
        attempt = self.roll_save('fort', tn=10, reason='to become stable')
        if attempt.success:
            self.remove_conditions('dying', source='damage')
            self.add_condition('stable', source='damage')
        return attempt.success

    def roll_save(self, save_type, tn=None, tn_name='DC', stealth=False,
                  reason=None, desc_override=None, **params):
        """
        Perform a saving throw.

        :param save_type: The save type (fortitude, reflex, will).
        :param tn: The target number to meet or exceed for success.
        :param tn_name: A description of the target number.
        :param stealth: Whether or not to hide the RPG notice.
        :param reason: Optional string describing why the save is needed.
        :param desc_override: Optionally override automatic notice string with
            a custom one.
        :type desc_override: list or str
        :param params: Parameters to pass when retrieving the save stat mods.

        :rtype: pathfinder.RollResult
        """
        save_type, tags = self.resolve_stat_name(save_type)
        if save_type not in ('fortitude', 'reflex', 'will'):
            raise pathfinder.errors.InvalidSave('Invalid save type: %s'
                                                % save_type)
        key = '__%s_save' % save_type
        if key in self._stat_cache:
            mods = self._stat_cache[key]
        else:
            save_base = self.get_stat_base(save_type, resolved=True)
            save_mods = self.get_stat_modifiers(save_type, **params)
            mods = OrderedDict([(save_type, save_base)])
            for name, mod in save_mods.iteritems():
                mods[self._part_name(name)] = mod
            self.cache_stat(key, mods)
        result = self.d20_roll(mods, target_number=tn)
        if not stealth:
            if desc_override is not None:
                if isinstance(desc_override, str):
                    notice = [desc_override]
                else:
                    notice = desc_override
            else:
                # Automatic notice generation.
                notice = [self, ' makes a ', '{y' + save_type, '{y check']
                if tn is not None:
                    tn_desc = ' vs ' + ("{y%s %s" % (tn_name, tn)).lstrip()
                    notice.append(tn_desc)
                if reason is not None:
                    notice.append(' ' + reason.strip())
                notice.append(': ')
                notice.append(result)
                if tn is not None:
                    notice.append(': ')
                    notice.append('{gSUCCESS' if result.success else '{rFAIL')
                else:
                    notice.append('.')
            self.rpg_notice(*notice)
        return result


    def add_xp(self, xp, stealth=False, force=True):
        if self.level > self.frozen_level and not force:
            if not stealth:
                self.tell('{yYou just missed out on {y', xp,
                          ' {yXP! {rYou cannot gain XP while levelling up!')
            return
        before = self.current_xp_level
        if xp > 0:
            self.xp += xp
            if not stealth:
                self.tell("{gYou gained {c", xp, "{g experience points!")
                if before < self.current_xp_level:
                    self.tell('{r*** {yYOU CAN LEVEL-UP! {r***')

    @property
    def current_xp_level(self):
        lvl = 0
        for xp in pathfinder.advancement.active_table():
            if self.xp >= xp:
                lvl += 1
            else:
                break
        return lvl

    @property
    def next_level_xp(self):
        current_lvl = self.current_xp_level
        table = pathfinder.advancement.active_table()
        if len(table) >= current_lvl:
            return table[current_lvl]
        else:
            return None

    @property
    def xp_to_next_level(self):
        return self.next_level_xp - self.xp

    def levelling_up(self):
        """
        :return: True if character is currently levelling up.
        :rtype: bool
        """
        return self.level > self.frozen_level

    def gain_ability(self, ability):
        previous = self.get_stat_base(ability)
        new = previous + 1
        self.set_stat(ability, new)
        a = ability.capitalize()
        self.tell('{gYour {m', a, '{g score is now {c', new, '{g.')

    def lose_ability(self, ability):
        previous = self.get_stat_base(ability)
        new = previous - 1
        self.set_stat(ability, new)
        a = ability.capitalize()
        self.tell('{yYour {m', a, '{y score is now {c', new, '{y.')

    def increment_stat(self, stat, amount=1):
        existing = self.get_stat(stat)
        self.set_stat(stat, existing + amount)

    def set_race(self, race):
        if self.race is not None:
            try:
                self.race.remove_from(self)
            except AttributeError:
                pathfinder.logger.error("Invalid race for %r: %r",
                                        self, self.race, exc_info=True)
        self.race = race
        if race is not None:
            race.apply_to(self)
        self.clear_stat_cache()

    def reset_character(self, wipe_xp=False):
        while self.level > 0:
            self.undo_level(stealth=True)
        self.set_race(None)
        self.stats = {}
        if wipe_xp:
            self.xp = 0
            self.tell('You have {r0 {nXP.')
        self.clear_stat_cache()
        self.tell('{rYour character sheet has been reset!')

    def add_level(self, class_, ability=None):
        self._check_attr('levels', [])
        self.levels.append(class_)
        self.clear_stat_cache()
        ability_increase = (self.level % 4 == 0)
        if ability_increase:
            if ability is None:
                ability = random.choice(pathfinder.abilities)
            if ability not in pathfinder.abilities:
                raise ValueError("Invalid ability: %s" % ability)
            self.gain_ability(ability)
            self.level_log(self.level, 'ability', self, ability)
        class_.apply_level(self.classes[class_], self)
        self.tell('{gYou have gained a level of {m', class_.name, '{g.')

    def undo_level_ability(self, char, level, ability):
        char.lose_ability(ability)

    def undo_level(self, stealth=False):
        """
        Undo all the character changes tha resulted from the last level gained.
        """
        level = self.level
        level_changes = self.level_history.get(level, {})
        # Apply changes in reverse order of how they occurred.
        activities = level_changes.keys()
        activities.reverse()
        for activity in activities:
            fname = "undo_level_%s" % activity
            for change in level_changes[activity]:
                source, data = change
                getattr(source, fname)(self, level, *data)
        # Use .items() instead of .iteritems() because we will be editing.
        for skill, ranks in self.level_up_skills.items():
            self.remove_skill_rank(skill, ranks)
        del self.level_history[level]
        if self.frozen_level < self.level and not stealth:
            self.tell('{yLevel-up changes have been cancelled.')
        self.levels.pop()
        self.clear_stat_cache()
        self.frozen_level = self.level
        if not stealth:
            self.tell('{yYou are currently at level {c', self.level, '{y.')

    def level_log(self, level, activity, source, *data):
        self._check_attr('level_history', {})
        if level not in self.level_history:
            self.level_history[level] = OrderedDict()
        if activity not in self.level_history[level]:
            self.level_history[level][activity] = []
        self.level_history[level][activity].append((source, data))

    def finalize_level(self):
        level = self.level
        self.level_log(level, 'skills', self, self.level_up_skills.items())
        self.level_up_skills = {}
        self.level_log(level, 'feats', self, self.level_up_feats)
        self.level_up_feats = []
        self.frozen_level = level
        self.tell('{gYou have finalized level {y', level, '{g!')
        self.tell('You may no longer make changes to your character sheet.')

    def gain_hitpoints(self, points):
        if isinstance(points, basestring):
            points, d = self.roll(points, desc=True)
            self.tell('You roll for hit points: {c', d)
        self.permanent_hit_points += points
        self.tell('You gain {y', points, '{n hit points, for a total of {g',
                  self.permanent_hit_points, '{n.')
        return points

    def lose_hitpoints(self, points):
        self.permanent_hit_points -= points
        self.tell('You lose {y', points, '{n hit points, for a total of {g',
                  self.permanent_hit_points, '{n.')

    def class_skills(self):
        if '__class_skills' in self._stat_cache:
            return self._stat_cache['__class_skills']
        skills = []
        for class_ in self.classes.iterkeys():
            for skill_name in class_.skills:
                try:
                    skill = pathfinder.data.match(skill_name, types=('skill',))
                except mudsling.errors.MatchError:
                    # Exclude broken skill name.
                    continue
                if skills not in skills:
                    skills.append(skill)
        self._check_attr('_stat_cache', {})
        self._stat_cache['__class_skills'] = skills
        return skills

    def add_feat(self, feat_class, subtype=None, source=None, slot=None):
        self._check_attr('_feats', [])
        self._check_attr('level_up_feats', [])
        if source is 'slot' and slot is None:
            compatible = self.compatible_feat_slots(feat_class, subtype)
            if compatible:
                slot = compatible[0]
            else:
                msg = "No feat slot available for %s" % feat_class.name
                raise pathfinder.errors.CharacterError(msg)
        existing = self.get_feat(feat_class, subtype)
        if existing is not None:
            if source == 'slot' and 'slot' in existing.sources:
                msg = "Feat can only occupy one feat slot."
                raise pathfinder.errors.CharacterError(msg)
            existing.sources.append(source)
        else:
            feat = feat_class(subtype, source, slot)
            feat.apply_to(self)
            self._feats.append(feat)
            if source == 'slot':
                self.level_up_feats.append(feat)
            self.clear_stat_cache()
            self.tell("{gYou gain the {c", feat, "{g ", feat.feature_type, '.')

    def remove_feat(self, feat, source=None):
        """
        Remove a feat instance from a character. If the feat is provided by
        multiple sources, it may not actually be removed.

        :param feat: The feat INSTANCE to remove.
        :type feat: pathfinder.feats.Feat
        :param source: The source to remove in the case of a multi-source feat.
            If a non-None source is specified but is not in the feat's list of
            sources, then the feat will not be removed. If no source is given,
            and the feat is occupying a feat slot, the slot will be vacated.
        """
        if source is None and 'slot' in feat.sources:
            source = 'slot'
        if source is not None:
            if source in feat.sources:
                feat.sources.remove(source)
                if source == 'slot':
                    feat.slot = None
                    if feat in self.level_up_feats:
                        self.level_up_feats.remove(feat)
            else:
                # Specified source does not provide the feat.
                return
        if feat.sources:  # Something still keeping feat around. Abort!
            return
        # Remove the feat that is no longer provided by anything.
        self._feats.remove(feat)
        feat.remove_from(self)
        self.clear_stat_cache()
        self.tell("{yYou lose the {c", feat, "{y ", feat.feature_type, '.')

    def add_feat_slot(self, type='general', slots=1):
        self._check_attr('feat_slots', {})
        if type not in self.feat_slots:
            self.feat_slots[type] = slots
        else:
            self.feat_slots[type] += slots

    def remove_feat_slot(self, type='general', slots=1):
        self._check_attr('feat_slots', {})
        if type in self.feat_slots:
            if slots >= self.feat_slots[type]:
                del self.feat_slots[type]
            else:
                self.feat_slots[type] -= slots

    def feats_by_slot(self):
        slots = {}
        for slot_type in self.feat_slots.iterkeys():
            slots[slot_type] = []
        for feat in self._feats:
            if feat.slot is not None:
                if feat.slot not in slots:
                    slots[feat.slot] = []
                slots[feat.slot].append(feat)
        return slots

    def available_feat_slots(self):
        existing = self.feats_by_slot()
        available = {}
        for slot_type, count in self.feat_slots.iteritems():
            available[slot_type] = count - len(existing[slot_type])
        return available

    def compatible_feat_slots(self, feat_class, subtype=None):
        return [st for st, c in self.available_feat_slots().iteritems()
                if c > 0 and st in feat_class.compatible_slots(subtype)]

    def get_feat(self, feat, subtype=None):
        """
        Return the feat instance if this character has the specified feat.

        If '*' is passed for subtype, then first feat of the feat class found
        will be returned. Useful for determining if character has a feat with
        any subtype.

        :param feat: The feat class or name of the feat.
        :param subtype: The subtype. Overrides subtype in feat name.
        """
        if isinstance(feat, basestring):
            feat, subtype_ = pathfinder.parse_feat(feat)
            if subtype is None and subtype_ is not None:
                subtype = subtype_
        subtype = subtype.lower() if isinstance(subtype, basestring) else None
        for f in self.feats:
            f_subtype = f.subtype.lower() if f.subtype is not None else None
            if f.__class__ == feat and (f_subtype == subtype
                                        or subtype == '*'):
                return f
        return None

    def has_feat(self, feat, subtype=None):
        return self.get_feat(feat, subtype) is not None

    def has_feature(self, name, subtype=None):
        name = name.lower()
        for feature in self.features:
            if feature.name.lower() == name:
                if hasattr(feature, 'subtype'):
                    if feature.subtype == subtype:
                        return True
                elif subtype is None:
                    return True
        return False

    def gain_skill_points(self, points):
        self.skill_points += points
        self.tell('You gain {y', points, ' {mskill {npoints!')

    def lose_skill_points(self, points):
        self.skill_points -= points
        self.tell('You lose {r', points, ' {mskill {npoints!')

    def add_skill_rank(self, skill, ranks=1, level_up=True,
                       deduct_points=True):
        self._check_attr('skills', {})
        self._check_attr('level_up_skills', {})
        skill_current = self.skills.get(skill, 0)
        if skill_current >= self.level:
            raise pathfinder.errors.SkillError(
                "Cannot train skills above your level.")
        if deduct_points:
            if self.skill_points < ranks:
                raise pathfinder.errors.SkillError(
                    "Insufficient skill points.")
            self.skill_points -= ranks
        self.skills[skill] = skill_current + ranks
        if level_up:
            lvlup_current = self.level_up_skills.get(skill, 0)
            self.level_up_skills[skill] = lvlup_current + ranks
        self.clear_stat_cache()
        self.tell('You are now trained to rank {g', skill_current + ranks,
                  '{n in {c', skill, '{n (effective check bonus: {y',
                  pathfinder.format_modifier(self.skill_base_bonus(skill)),
                  '{n).')

    def remove_skill_rank(self, skill, ranks=1, level_up=True,
                          credit_points=True):
        self._check_attr('skills', {})
        self._check_attr('level_up_skills', {})
        skill_current = self.skills.get(skill, 0)
        if skill_current < ranks:
            raise pathfinder.errors.SkillError("No ranks of %s to remove."
                                               % skill.name)
        if level_up:
            lvlup_current = self.level_up_skills.get(skill, 0)
            if lvlup_current < ranks:
                msg = "Cannot remove skill ranks gained in a previous level."
                raise pathfinder.errors.SkillError(msg)
            self.level_up_skills[skill] = lvlup_current - ranks
            if not self.level_up_skills[skill]:
                del self.level_up_skills[skill]
        if credit_points:
            self.skill_points += ranks
        self.skills[skill] -= ranks
        if self.skills[skill] == 0:
            del self.skills[skill]
        self.clear_stat_cache()
        self.tell('You are now trained to rank {g', skill_current - ranks,
                  '{n in {c', skill, '{n (effective check bonus: {y',
                  pathfinder.format_modifier(self.skill_base_bonus(skill)),
                  '{n).')

    def skill_ranks(self, skill):
        """
        How many ranks of training does the character have in the skill?
        """
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        return self.skills.get(skill, 0)

    def skill_base_bonus(self, skill):
        """
        Get the base skill bonus. Does not include effects.

        Base bonus = ranks + ability modifier + class skill bonus (if any)
        """
        if isinstance(skill, basestring):
            skill = pathfinder.data.match(skill, types=('skill',))
        trained = self.skill_ranks(skill)
        ability_modifier = self.get_stat(skill.ability + ' mod')
        bonus = 3 if trained and skill in self.class_skills() else 0
        return trained + ability_modifier + bonus

    def resolve_stat_name(self, name):
        name = name.lower()
        m = self._save_re.match(name)
        if m:
            return self.resolve_stat_name(m.groups()[0])
        if not name.startswith('all'):
            # Exclude 'all skill checks', 'all ability checks', etc.
            m = self._skill_check_re.match(name)
            if m:
                name, extra = m.groups()
                return name, ('check',) if extra else ()
        return super(Character, self).resolve_stat_name(name)

    def get_all_stat_names(self):
        names = super(Character, self).get_all_stat_names()
        names.update(pathfinder.abilities)
        names.update(pathfinder.abil_short)
        names.update(pathfinder.data.names('skill'))
        return names

    def best_class_stat(self, stat):
        options = [0]
        options.extend(getattr(c.levels[l - 1], stat)
                       for c, l in self.classes.iteritems())
        return max(options)

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat == 'level' or stat == 'hit dice':
            return len(self.levels)
        if stat in self._abil_modifier_stats:
            return math.trunc(self.get_stat(stat.split(' ')[0]) / 2 - 5)
        elif stat in self._abil_bonus_stats:
            mod = math.trunc(self.get_stat(stat.split(' ')[0]) / 2 - 5)
            return max(0, mod)
        elif stat == 'size modifier':
            return self.size_category.size_modifier
        elif stat == 'special size modifier':
            return self.size_category.special_size_modifier
        elif stat == 'base attack bonus':
            return self.best_class_stat('bab')
        elif stat == 'fortitude':
            return self.best_class_stat('fort')
        elif stat == 'reflex':
            return self.best_class_stat('ref')
        elif stat == 'will':
            return self.best_class_stat('will')
        elif stat == 'defensive dex mod':
            # Normally, the dex MODIFIER (bonus + penalties) is applied to AC,
            # but character can lose dex BONUSES (positive only) to AC.
            dex_mod = min(self.get_stat('dex mod'),
                          self.get_stat('armor dex limit'))
            if not self.can_use_defensive_dex_bonus:
                return min(0, dex_mod)
            else:
                return dex_mod
        elif stat in pathfinder.data.registry['skill']:
            return self.skill_base_bonus(stat)
        else:
            m = self._class_lvl_re.match(stat)
            if m:
                class_name = m.groups()[0].lower()
                for cls, levels in self.classes.iteritems():
                    if cls.name.lower == class_name:
                        return levels
                return 0
            return super(Character, self).get_stat_base(stat, resolved=True)

    def get_stat_modifiers(self, stat, **params):
        mods = super(Character, self).get_stat_modifiers(stat, **params)
        resolved, tags = self.resolve_stat_name(stat)
        if resolved in pathfinder.data.registry['skill']:
            mods.update(self.get_stat_modifiers('all skill checks'))
            #: :type: pathfinder.skills.Skill
            skill = pathfinder.data.registry['skill'][resolved]
            modstat = 'all %s-based skill checks'
            modstat %= self.resolve_stat_name(skill.ability)[0]
            mods.update(self.get_stat_modifiers(modstat, **params))
        elif 'check' in tags and resolved in pathfinder.abilities:
            mods.update(self.get_stat_modifiers('all %s checks' % resolved))
        elif resolved in ('melee attack', 'ranged attack'):
            mods.update(self.get_stat_modifiers('all attacks'))
        elif resolved in ('fortitude', 'reflex', 'will'):
            mods.update(self.get_stat_modifiers('all saves'))
        return mods

    def check_prerequisites(self, prerequisites):
        return pathfinder.prerequisites.check(prerequisites, self)

    def tell_prerequisite_failures(self, failures, subject):
        fails = str_utils.english_list(["{r%s{n" % f for f in failures])
        self.tell("{yYou do not meet these requirements for "
                  "{c", subject, "{y: ", fails)

    def spoken_languages(self):
        e = self.trigger_event(events.spoken_languages, languages=[])
        return e.languages

    def auto_level(self):
        """
        Automatically level up.
        """
        if not self.current_xp_level > self.level:
            return False
        if self.frozen_level < 1:
            self.process_input("+abilities random")
            self.process_input("+race %s" % random.choice(
                pathfinder.data.registry['race'].values()).name)
            self.process_input("+age 20 years")
            self.process_input("+gender %s" % random.choice(self.race.genders))
            self.process_input("+height 6'")
            self.process_input("+weight 150 lbs")
            char_class = random.choice(
                pathfinder.data.registry['class'].values())
        else:
            char_class = self.classes[0]
        abil = random.choice(pathfinder.abilities)
        if self.current_xp_level % 4 == 0:
            self.process_input("+level-up %s +%s" % (char_class.name, abil))
        else:
            self.process_input("+level-up %s" % char_class.name)
        class_skills = self.class_skills()
        skill_pool = list(class_skills)
        skill_pool.extend(pathfinder.data.registry['skill'].itervalues())
        tries = 0
        while self.skill_points:
            skill = random.choice(skill_pool)
            try:
                self.add_skill_rank(skill)
            except pathfinder.errors.SkillError:
                tries += 1
                if tries >= 3:
                    break
        # todo: feats
        self.process_input("+finalize/confirm")

    def join_battle(self, battle):
        battle.add_combatant(self.ref())

    @property
    def num_attacks(self):
        """
        The number of attacks this character can perform per turn.
        :rtype: int
        """
        return 1 + math.trunc((self.bab - 1) / 5)

    def body_region_worn(self, region=None):
        """
        Get the objects occupying each body region.

        :param region: Optional region whose wearables to return.
        :type region: str or None

        :return: A list of a single region's wearables, or a dictionary of
            every region and their corresponding wearables.
        :rtype: list or dict of list of wearables.Wearable
        """
        region = region.lower() if isinstance(region, str) else None
        eq = pathfinder.equipment.WearableEquipment
        in_reg = lambda w, r: w.isa(eq) and r in w.body_regions
        worn = {}
        for br in self.body_regions:
            if region is None or region == br:
                worn[br] = [i for i in self.wearing if in_reg(i, br)]
        if region is not None:
            return worn.get(region, [])
        return worn

    def body_region_layers(self, region=None):
        """
        Get the number of layers being worn on a specific body region.

        :param region: Optional body region to get the layer value for.
        :type region: str or None

        :return: The layer value for a given region, or a dictionary of all
            regions and how many layers are on each.
        :rtype: float or list of wearables.Wearable
        """
        region = region.lower() if isinstance(region, str) else None
        worn = self.body_region_worn(region)
        if region is not None:
            worn = {region: worn}
        layers = {}
        for r, items in worn.iteritems():
            layers[r] = sum(w.layer_value for w in items)
        if region is not None:
            return layers[region]
        return layers

    def covering_wearable(self, wearable=None):
        """
        Get a list of wearables covering the specified wearable.

        :param wearable: The wearable for which to find covering wearables. If
            no wearable is specified, then a dictionary of all wearables and the
            other wearables covering them is returned instead.

        :return: List of wearables covering the specified wearable, or a dict
            whose keys are wearables, and values are a list of the wearables
            covering the wearable in the key.
        :rtype: list of pathfinder.equipment.WearableEquipment or dict
        """
        wearable = wearable.ref() if wearable is not None else None
        covering = {}
        for region, items in self.body_region_worn().iteritems():
            last = len(items) - 1
            for i, item in enumerate(items):
                if item not in covering:
                    covering[item] = []
                if i < last and (wearable is None or wearable == item):
                    covering[item].extend(items[i + 1:])
        out = dict((k, seq_utils.unique(v)) for k, v in covering.iteritems())
        if wearable is not None:
            return out.get(wearable, [])
        else:
            return out

    def visible_wearables(self, viewer=None):
        """
        Get a list of wearables on this character that are visible (exposed).

        :return: List of wearables that are visible.
        :rtype: list of wearables.Wearable
        """
        covering = self.covering_wearable()
        visible = list(self.wearing)
        for wearable in self.wearing:
            if wearable in visible and len(covering.get(wearable, ())) > 0:
                visible.remove(wearable)
        return visible

    @property
    def wielded_weapons(self):
        return seq_utils.unique(o for o in self.hands.itervalues()
                                if o is not None)

    @property
    def primary_hand(self):
        hands = self.hands.keys()
        return hands[0] if hands else None

    def is_wielding_obj(self, obj):
        """
        Determine if the specified object is currently wielded by this char.

        :param obj: The object to inquire about.
        :rtype: bool
        """
        return obj.ref() in self.wielded_weapons

    def hands_wielding(self, obj):
        """
        Obtain a list of the hands that participating in wielding the specified
        object.

        :param obj: The object being wielded.
        :rtype: tuple of str

        :raises: pathfinder.errors.NotWielding
        """
        obj = obj.ref()
        if not self.is_wielding_obj(obj):
            raise pathfinder.errors.NotWielding(obj=obj)
        return tuple(h for h, o in self.hands.iteritems() if o == obj)

    def wield(self, obj, hands=None, stealth=False):
        """
        Wield specified object in the optionally specified body region (which
        must be either .primary_hand or .off_hand.

        :param obj: The object to wield. Must be a pathfinder.objects.Thing.
        :type obj: pathfinder.things.Thing

        :param hands: The wielding regions to wield the object in. If None,
            then select the first available wielding regions.
        :type hands: None or str or list of str or tuple of str

        :raises: pathfinder.errors.ObjectNotwieldable
        :raises: pathfinder.errors.InsufficientFreeHands
        :raises: pathfinder.errors.HandNotAvailable
        """
        obj = obj.ref()
        if not obj.isa(pathfinder.things.Thing):
            raise pathfinder.errors.ObjectNotWieldable()
        elif obj not in self.contents:
            msg = 'You must be holding an object to wield it.'
            raise pathfinder.errors.ObjectNotWieldable(msg)
        elif obj in self.wielded_weapons:
            msg = 'You are already wielding %s.' % self.name_for(obj)
            raise pathfinder.errors.AlreadyWielding(msg)
        if isinstance(hands, str):
            hands = [hands]
        # Some weapons require two hands.
        WieldType = pathfinder.combat.WieldType
        req_len = 2 if obj.wield_type == WieldType.TwoHanded else 1
        if hands is None:
            hands = [None] * req_len
        else:
            assert isinstance(hands, (list, tuple))
            # Pad out the list to the required number of hands.
            hands = (list(hands) + [None] * (req_len - len(hands)))
        # Limit to required number of hands.
        hands = hands[:req_len]
        # Fill out any empty hand assignments.
        for wield_region, wielded in self.hands.iteritems():
            if wielded is None:
                hands[hands.index(None)] = wield_region
                if None not in hands:
                    break
        if None in hands:
            raise pathfinder.errors.InsufficientFreeHands()
        for hand in hands:
            if self.hands[hand] is not None:
                raise pathfinder.errors.HandNotAvailable(hand=hand)
        if 'hands' not in self.__dict__:
            self.hands = OrderedDict(self.hands)
        for hand in hands:
            self.hands[hand] = obj
        if not stealth:
            self.emit_message('wield', actor=self.ref(), obj=obj,
                              hands=str_utils.english_list(hands))

    def unwield(self, obj, stealth=False):
        """
        Stop wielding the specified object.

        :param obj: The object to stop wielding.
        :type obj: pathfinder.things.Thing
        """
        obj = obj.ref()
        for hand in self.hands_wielding(obj):
            self.hands[hand] = None
        if not stealth:
            self.emit_message('unwield', actor=self.ref(), obj=obj)

    @property
    def unarmed_critical_threat(self):
        event = self.trigger_event(events.unarmed_crit_threat)
        return min(20, 20, *[v for v in event.responses.itervalues()
                             if v is not None])

    @property
    def unarmed_critical_multiplier(self):
        event = self.trigger_event(events.unarmed_crit_multiplier)
        return max(2, 2, *[v for v in event.responses.itervalues()
                           if v is not None])

    @property
    def unarmed_weapon(self):
        return UnarmedWeapon(self)



# Assign commands here to avoid circular import issues.
from .commands import character as character_commands
from .commands import combat as combat_commands
Character.private_commands = all_commands(character_commands, combat_commands)
del character_commands, combat_commands
