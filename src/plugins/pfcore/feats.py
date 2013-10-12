from mudsling.utils.sequence import CaselessDict

from pathfinder.feats import Feat
from pathfinder.modifiers import modifiers
import pathfinder.data


class Acrobatic(Feat):
    name = 'Acrobatic'
    modifiers = modifiers(
        '+2 bonus on Acrobatics checks',
        '+2 bonus on Fly checks'
    )


class AgileManeuvers(Feat):
    name = 'Agile Maneuvers'
    type = 'combat'
    modifiers = modifiers('+max(STR mod, DEX mod) - STR mod to CMB')


class Altertness(Feat):
    name = 'Alertness'
    modifiers = modifiers(
        '+2 bonus on Perception checks',
        '+2 bonus on Sense Motive checks'
    )


# class AlignmentChannel(Feat):
#     name = 'Alignment Channel'
#     prerequisites = ["Channel Energy"]
#     multiple = True
#     subtypes = ['chas', 'evil', 'good', 'law']


class AnimalAffinity(Feat):
    name = 'Animal Affinity'
    modifiers = modifiers(
        '+2 bonus on Handle Animal checks',
        '+2 bonus on Ride checks'
    )


# class ArcaneArmorTraining(Feat):
#     name = 'Arcane Armor Training'
#     type = 'combat'
#     prerequisites = [
#         'Armor Proficiency, Light',
#         'caster level 3rd'
#     ]
#     modifiers = modifiers('-10% to arcane spell failure chance')


# class ArcaneArmorMastery(Feat):
#     name = 'Arcane Armor Mastery'
#     type = 'combat'
#     prerequisites = [
#         'Arcane Armor Training',
#         'Armor Proficiency, Medium',
#         'caster level 7th'
#     ]
#     modifiers = modifiers('-10% to arcane spell failure chance')


# class ArcaneStrike(Feat):
#     name = 'Arcane Strike'
#     prerequisites = ['Cast arcane spells']


class ArmorProficiencyLight(Feat):
    name = 'Armor Proficiency, Light'


class ArmorProficiencyMedium(Feat):
    name = 'Armor Proficiency, Medium'
    _prerequisites = ['Armor Proficiency, Light']


class ArmorProficiencyHeavy(Feat):
    name = 'Armor Proficiency, Heavy'
    _prerequisites = ['Armor Proficiency, Medium']


class Athletic(Feat):
    name = 'Athletic'
    modifiers = modifiers(
        '+2 bonus on Climb checks',
        '+2 bonus on Swim checks'
    )


# class AugmentSummoning(Feat):
#     name = 'Augment Summoning'
#     prerequisites = ['Spell Focus (conjuration)']


class BlindFight(Feat):
    name = 'Blind-Fight'
    type = 'combat'
    modifiers = modifiers('-10 to concealment miss chance')


class CatchOffGuard(Feat):
    name = "Catch Off-Guard"
    type = 'combat'
    modifiers = modifiers('+4 to improvised weapon modifier')


# class ChannelSmite(Feat):
#     name = 'Channel Smite'
#     type = 'combat'
#     prerequisites = ['Channel Energy']


# class CombatCasting(Feat):
#     name = 'Combat Casting'
#     modifiers = modifiers('+4 bonus to defensive concentration')


class CombatExpertise(Feat):
    name = 'Combat Expertise'
    type = 'combat'
    _prerequisites = ['Intelligence 13']


class ImprovedDisarm(Feat):
    name = 'Improved Disarm'
    type = 'combat'
    _prerequisites = ['Combat Expertise']
    modifiers = modifiers('+2 bonus on disarm attempts')


class GreaterDisarm(Feat):
    name = 'Greater Disarm'
    type = 'combat'
    _prerequisites = [
        'Improved Disarm',
        'BAB 6'
    ]
    modifiers = modifiers('+4 bonus on disarm attempts')


class ImprovedFeint(Feat):
    name = 'Improved Feint'
    type = 'combat'
    _prerequisites = ['Combat Expertise']
    description = "Feint as a move action."


class GreaterFeint(Feat):
    name = 'Greater Feint'
    type = 'combat'
    _prerequisites = [
        'Improved Feint',
        'BAB 6'
    ]
    description = "Target loses DEX bonus for entire round."


class ImprovedTrip(Feat):
    name = 'Improved Trip'
    type = 'combat'
    _prerequisites = ['Combat Expertise']
    description = "Tripping does not provoke attacks."
    modifiers = modifiers("+2 bonus on trip attempts")


class GreaterTrip(Feat):
    name = 'Greater Trip'
    type = 'combat'
    _prerequisites = [
        'Improved Trip',
        'BAB 6'
    ]
    description = "Successful trip is followed by an attack against target."
    modifiers = modifiers("+2 bonus on trip attempts")


class WhirlwindAttack(Feat):
    name = 'Whirlwind Attack'
    type = 'combat'
    _prerequisites = [
        'Dexterity 13',
        'Combat Expertise',
        'Sprint Attack',
        'BAB 4'
    ]
    description = "Make melee attack against all foes within reach."


class CombatReflexes(Feat):
    name = 'Combat Reflexes'
    type = 'combat'
    _prerequisites = ['BAB 9']
    description = "Make additional attacks of opportunity equal to DEX bonus."


class CriticalFocus(Feat):
    name = 'Critical Focus'
    type = 'combat'
    _prerequisites = ['BAB 9']
    modifiers = modifiers('+4 bonus to critical confirmation')


class DeadlyAim(Feat):
    name = 'Deadly Aim'
    type = 'combat'
    _prerequisites = [
        'Dexterity 13',
        'BAB 1'
    ]
    description = "Sacrifice -1 ranged accuracy to do +2 more damage."


class Deceitful(Feat):
    name = 'Deceitful'
    modifiers = modifiers(
        '+2 bonus on Bluff checks',
        '+2 bonus to Disguise checks'
    )


class DefensiveCombatTraining(Feat):
    name = 'Defensive Combat Training'
    type = 'combat'
    description = 'You excel at defending yourself from combat maneuvers.'
    modifiers = modifiers('+max(BAB, HD) - BAB to CMD')


class DeftHands(Feat):
    name = 'Deft Hands'
    modifiers = modifiers(
        '+2 bonus on Disable Device checks',
        '+2 bonus on Sleight of Hand checks'
    )


# class Disruptive(Feat):
#     name = 'Disruptive'
#     type = 'combat'
#     prerequisites = ['6th-level Fighter']
#     description = "Adjacent enemies have difficulty concentrating to cast."
#
#
# class Spellbreaker(Feat):
#     name = 'Spellbreaker'
#     type = 'combat'
#     prerequisites = ['Disruptive', '10th-level Fighter']
#     description = "Enemies provoke attacks if their spells fail."


class Dodge(Feat):
    name = 'Dodge'
    type = 'combat'
    _prerequisites = ['Dexterity 13']
    modifiers = modifiers('+1 dodge bonus to AC')


class Mobility(Feat):
    name = 'Mobility'
    type = 'combat'
    _prerequisites = ['Dodge']
    modifiers = modifiers(
        '+4 to AC against attacks of opportunity from movement'
    )


class SpringAttack(Feat):
    name = 'Spring Attack'
    type = 'combat'
    _prerequisites = ['Mobility', 'BAB 4']


# class ElementalChannel(Feat):
#     name = 'Elemental Channel'
#     prerequisites = ['Channel Energy']


class Endurance(Feat):
    name = 'Endurance'
    description = "+4 bonus on checks to avoid nonlethal damage."


class Diehard(Feat):
    name = 'Diehard'
    _prerequisites = ['Endurance']
    description = "Automatically stabilize and remain concious below 0 hp."


# class EschewMaterials(Feat):
#     name = 'Eschew Materials'
#     description = "No more need for materials to cast spells."


class ExoticWeaponProficiency(Feat):
    name = 'Exotic Weapon Proficiency'
    type = 'combat'
    _prerequisites = ['BAB 1']


# class ExtraChannel(Feat):
#     name = 'Extra Channel'
#     prerequisites = ['Channel Energy']
#     modifiers = modifiers("+2 channel energy uses")


# class ExtraKi(Feat):
#     name = 'Extra Ki'
#     prerequisites = ['Ki Pool']
#     modifiers = modifiers("+2 ki pool")


# class ExtraLayOnHands(Feat):
#     name = 'Extra Lay On Hands'
#     prerequisites = ['Lay On Hands']
#     modifiers = modifiers("+2 lay on hands uses")


# class FatiguedMercy(Feat):
#     name = "Fatigued Mercy"
#     type = 'mercy'
#     prerequisites = ['3rd-level Paladin']
#
#
# class ShakenMercy(Feat):
#     name = "Shaken Mercy"
#     type = 'mercy'
#     prerequisites = ['3rd-level Paladin']
#
#
# class SickenedMercy(Feat):
#     name = 'Sickened Mercy'
#     type = 'mercy'
#     prerequisites = ['3rd-level Paladin']
#
#
# class DazedMercy(Feat):
#     name = 'Dazed Mercy'
#     type = 'mercy'
#     prerequisites = ['6th-level Paladin']
#
#
# class DiseasedMercy(Feat):
#     name = 'Diseased Mercy'
#     type = 'mercy'
#     prerequisites = ['6th-level Paladin']
#
#
# class StaggeredMercy(Feat):
#     name = 'Staggered Mercy'
#     type = 'mercy'
#     prerequisites = ['6th-level Paladin']
#
#
# class CursedMercy(Feat):
#     name = 'Cursed Mercy'
#     type = 'mercy'
#     prerequisites = ['9th-level Paladin']
#
#
# class ExhaustedMercy(Feat):
#     name = 'Exhausted Mercy'
#     type = 'mercy'
#     prerequisites = ['9th-level Paladin']
#
#
# class FrightenedMercy(Feat):
#     name = 'Frightened Mercy'
#     type = 'mercy'
#     prerequisites = ['9th-level Paladin']
#
#
# class NauseatedMercy(Feat):
#     name = 'Nauseated Mercy'
#     type = 'mercy'
#     prerequisites = ['9th-level Paladin']
#
#
# class PoisonedMercy(Feat):
#     name = 'Poisoned Mercy'
#     type = 'mercy'
#     prerequisites = ['9th-level Paladin']
#
#
# class BlindedMercy(Feat):
#     name = 'Blinded Mercy'
#     type = 'mercy'
#     prerequisites = ['12th-level Paladin']
#
#
# class DeafenedMercy(Feat):
#     name = 'Deafened Mercy'
#     type = 'mercy'
#     prerequisites = ['12th-level Paladin']
#
#
# class ParalyzedMercy(Feat):
#     name = 'Paralyzed Mercy'
#     type = 'mercy'
#     prerequisites = ['12th-level Paladin']
#
#
# class StunnedMercy(Feat):
#     name = 'Stunned Mercy'
#     type = 'mercy'
#     prerequisites = ['12th-level Paladin']


class ExtraPerformance(Feat):
    name = "Extra Performance"
    _prerequisites = ['Bardic Performance']
    modifiers = modifiers('+6 to rounds of bardic performance')


class ExtraRage(Feat):
    name = "Extra Rage"
    _prerequisites = ['Rage']
    modifiers = modifiers('+6 to rounds of rage')


class GreatFortitude(Feat):
    name = "Great Fortitude"
    modifiers = modifiers('+2 on Fortitude saves')


class ImprovedGreatFortitude(Feat):
    name = "Improved Great Fortitude"
    _prerequisites = ['Great Fortitude']
    modifiers = modifiers('+2 on Fortitude saves')


# class ImprovedChannel(Feat):
#     name = "Improved Channel"
#     prerequisites = ['Channel Energy']
#     modifiers = modifiers('+2 to channel energy DC')


# class ImprovedCounterspell(Feat):
#     name = "Improved Counterspell"
#     description = "Counter spells with any spell from the same school."


class ImprovedCritical(Feat):
    name = 'Improved Critical'
    type = 'combat'
    _prerequisites = ['BAB 8']
    multiple = True
    subtypes = ()  # todo: Dynamically load weapon types
    description = "Double critical threat of a weapon type."


class ImprovedInitiative(Feat):
    name = "Improved Initiative"
    type = "combat"
    modifiers = modifiers('+4 bonus to initiative')


class ImprovedUnarmedStrike(Feat):
    name = "Improved Unarmed Strike"
    type = "combat"
    modifiers = modifiers('+4 to lethal unarmed strike')


class DeflectArrows(Feat):
    name = "Deflect Arrows"
    type = "combat"
    _prerequisites = ['Dexterity 13', 'Improved Unarmed Strike']
    description = "Avoid one arrow attack per combat round."


class SnatchArrows(Feat):
    name = "Snatch Arrows"
    type = "combat"
    _prerequisites = ['Dexterity 15', 'Deflect Arrows']
    description = "Catch one arrow per combat round."


class ImprovedGrapple(Feat):
    name = "Improved Grapple"
    type = "combat"
    _prerequisites = ['Dexterity 13', 'Improved Unarmed Strike']
    modifiers = modifiers('+2 bonus on grapple attempts')


class GreaterGrapple(Feat):
    name = "Greater Grapple"
    type = "combat"
    _prerequisites = ['BAB 6', 'Improved Grapple']
    modifiers = modifiers('+2 bonus on grapple attempts')


class ScorpionStyle(Feat):
    name = "Scorpion Style"
    type = "combat"
    _prerequisites = ['Improved Unarmed Strike']
    description = "Melee attack to prevent opponent from moving for 2 turns."


class FistOfGorgon(Feat):
    name = "Fist of Gorgon"
    type = "combat"
    _prerequisites = ['Scorpion Style', 'BAB 6']
    description = "Stagger an opponent affected by Scorpion Style."


class WrathOfMedusa(Feat):
    name = "Wrath of Medusa"
    type = "combat"
    _prerequisites = ['Fist of Gorgon', 'BAB 11']
    description = "Stun a staggered target."


class StunningFist(Feat):
    name = 'Stunning Fist'
    type = 'combat'
    _prerequisites = ['Dexterity 13', 'Wisdom 13', 'Improved Unarmed Strike',
                      'BAB 8']
    description = "Stun opponent with unarmed strike."


class ImprovisedWeaponMastery(Feat):
    name = 'Improvised Weapon Mastery'
    type = 'combat'
    _prerequisites = ['Catch Off-Guard', 'BAB 8']
    modifiers = modifiers('+1d4 to improvised weapon damage')


class IntimidatingProwess(Feat):
    name = 'Intimidating Prowess'
    type = 'combat'
    modifiers = modifiers('+STR mod to Intimidate skill checks')


class IronWill(Feat):
    name = 'Iron Will'
    modifiers = modifiers('+2 bonus on Will saves')


class ImprovedIronWill(Feat):
    name = 'Improved Iron Will'
    _prerequisites = ['Iron Will']
    modifiers = modifiers('+2 bonus on Will saves')


class LightningReflexes(Feat):
    name = 'Lightning Reflexes'
    modifiers = modifiers('+2 bonus on Reflex saves')


class ImprovedLightningReflexes(Feat):
    name = 'Improved Lightning Reflexes'
    _prerequisites = ['Lightning Reflexes']
    modifiers = modifiers('+2 bonus on Reflex saves')


class Lunge(Feat):
    name = "Lunge"
    type = 'combat'
    _prerequisites = ['BAB 6']
    description = "Melee attack at range carrying a -2 AC penalty."


# class MagicalAptitude(Feat):
#     name = 'Magical Aptitude'
#     modifiers = modifiers(
#         '+2 bonus on Spellcraft checks',
#         '+2 bonus on Use Magic Device checks'
#     )


class MartialWeaponProficiency(Feat):
    name = 'Martial Weapon Proficiency'
    type = 'combat'
    multiple = True
    subtypes = ()  # todo: Dynamic martial weapon list


class Persuasive(Feat):
    name = 'Persuasive'
    modifiers = modifiers(
        '+2 bonus on Diplomacy checks',
        '+2 bonus on Intimidate checks'
    )


class PointBlankShot(Feat):
    name = 'Point-Blank Shot'
    type = 'combat'
    description = "+1 bonus to ranged attacks inside weapon's range increment."


class FarShot(Feat):
    name = 'Far Shot'
    type = 'combat'
    _prerequisites = ['Point-Blank Shot']
    modifiers = modifiers('+1 to range increment modifier')


class PreciseShot(Feat):
    name = 'Precise Shot'
    type = 'combat'
    _prerequisites = ['Point-Blank Shot']
    modifiers = modifiers('+4 to shoot into melee modifier')


class ImprovedPreciseShot(Feat):
    name = 'Improved Precise Shot'
    type = 'combat'
    _prerequisites = ['Precise Shot', 'Dexterity 19', 'BAB 11']
    description = "Ignore all but total cover with ranged attacks."


class PinpointTargeting(Feat):
    name = 'Pinpoint Targeting'
    type = 'combat'
    _prerequisites = ['Improved Precise Shot', 'BAB 16']
    description = "Ignore target's armor with ranged attack when not moving."


class RapidShot(Feat):
    name = 'Rapid Shot'
    type = 'combat'
    _prerequisites = ['Dexterity 13', 'Point-Blank Shot']
    description = "Full-round ranged attack on multiple targets."


class PowerAttack(Feat):
    name = 'Power Attack'
    type = 'combat'
    _prerequisites = ['Strength 13', 'BAB 1']
    description = "Sacrifice accuracy for extra damage during melee."


class Cleave(Feat):
    name = 'Cleave'
    type = 'combat'
    _prerequisites = ['Power Attack']
    description = "Attempt to attack two targets at the cost of -2 to AC."


class GreatCleave(Feat):
    name = 'Great Cleave'
    type = 'combat'
    _prerequisites = ['Cleave', 'BAB 4']
    description = "Cleave more than two targets."


class ImprovedSunder(Feat):
    name = 'Improved Sunder'
    type = 'combat'
    _prerequisites = ['Power Attack']
    modifiers = modifiers("+2 on sunder attempts")


class GreaterSunder(Feat):
    name = 'Greater Sunder'
    type = 'combat'
    _prerequisites = ['Improved Sunder', 'BAB 6']
    modifiers = modifiers("+2 on sunder attempts")


class QuickDraw(Feat):
    name = 'Quick Draw'
    type = 'combat'
    _prerequisites = ['BAB 1']
    description = "Draw weapons as a free action."


class RapidReload(Feat):
    name = 'Rapid Reload'
    type = 'combat'
    description = "Reload a weapon as a free action."

    @classmethod
    def subtypes(cls):
        return {}  # todo: Dynamic list of reloadable weapon types.


class SelfSufficient(Feat):
    name = 'Self-Sufficient'
    modifiers = modifiers(
        '+2 bonus on Heal checks',
        '+2 bonus on Survival checks'
    )


class ShieldProficiency(Feat):
    name = 'Shield Proficiency'
    description = "Most shields' AC penalty only affects STR and DEX skills."


class ImprovedShieldBash(Feat):
    name = 'Improved Shield Bash'
    type = 'combat'
    _prerequisites = ['Shield Proficiency']


class ShieldFocus(Feat):
    name = 'Shield Focus'
    type = 'combat'
    _prerequisites = ['Shield Proficiency', 'BAB 1']
    description = "Increase the AC bonus granted by any shield by 1."


class GreaterShieldFocus(Feat):
    name = "Greater Shield Focus"
    type = 'combat'
    _prerequisites = ['Shield Focus', '8th-level Fighter']


class TowerShieldProficiency(Feat):
    name = "Tower Shield Proficiency"
    type = 'combat'
    _prerequisites = ['Shield Proficiency']
    description = "Tower shields' AC penalty only affects STR and DEX skills."


class SimpleWeaponProficiency(Feat):
    name = "Simple Weapon Proficiency"
    type = 'combat'
    description = "You are trained in the use of basic weapons."


class SkillFocus(Feat):
    name = 'Skill Focus'
    description = "You are particiularly adept at a chosen skill."
    multiple = True

    @classmethod
    def subtypes(cls):
        return CaselessDict(pathfinder.data.registry['skill'])

    def _skill_bonus(self, char):
        return

    def respond_to_event(self, event, responses):
        if event.name == 'stat mods':
            if event.stat == self.subtype.lower():
                bonus = 6 if event.obj.skill_ranks(self.subtype) >= 10 else 3
                event.modifiers[self] = bonus


# class SpellFocus(Feat):
#     name = 'Spell Focus'
#     description = "Spells you cast in chosen school are harder to resist."
#     multiple = True
#     # todo: Dynamic list of spell schools?


# class GreaterSpellFocus(Feat):
#     name = "Greater Spell Focus"
#     description = "Spells you cast in chosen school are very hard to resist."
#     multiple = True
#     # todo: Dynamic list of spell schools. (child of SpellFocus?)


class Stealthy(Feat):
    name = "Stealthy"
    modifiers = modifiers(
        "+2 bonus on Escape Artist checks",
        "+2 bonus on Stealth checks"
    )


class StrikeBack(Feat):
    name = "Strike Back"
    type = 'combat'
    _prerequisites = ['BAB 11']
    description = "You can strike back in response to any melee attack."


class Toughness(Feat):
    name = "Toughness"
    description = "3 HP, plus 1 HP per hit die beyond 3."
    modifiers = modifiers("+3 + max(0, HD - 3) to HP")


class TwoWeaponFighting(Feat):
    name = "Two-Weapon Fighting"
    type = 'combat'
    _prerequisites = ['Dexterity 15']
    description = "You can fight skillfully with a weapon in each hand."
    modifiers = modifiers(
        "+2 to two weapon primary hand modifier",
        "+6 to two weapon off-hand modifier"
    )


class ImprovedTwoWeaponFighting(Feat):
    name = "Improved Two-Weapon Fighting"
    type = 'combat'
    _prerequisites = ['Dexterity 17', 'Two-Weapon Fighting', 'BAB 6']
    description = "Gain an additional attack with off-hand weapon at -5."


class GreaterTwoWeaponFighting(Feat):
    name = "Greater Two-Weapon Fighting"
    type = 'combat'
    _prerequisites = ['Dexterity 19', 'Improved Two-Weapon Fighting', 'BAB 11']
    description = "Gain a third attack with off-hand weapon at -10."


class DoubleSlice(Feat):
    name = "Double Slice"
    type = 'combat'
    _prerequisites = ['Two-Weapon Fighting']
    description = "Use full Strength bonus to damage with off-hand weapon."
    modifiers = modifiers("+ceil(STR mod/2) to off-hand melee damage bonus")


class TwoWeaponRend(Feat):
    name = "Two-Weapon Rend"
    type = 'combat'
    _prerequisites = ['Double Slice', 'Improved Two-Weapon Fighting', 'BAB 11']
    description = "Rend a foe hit by both your weapons."


class TwoWeaponDefense(Feat):
    name = "Two-Weapon Defense"
    type = 'combat'
    _prerequisites = ['Two-Weapon Fighting']
    description = "Gain +1 shield bonus to AC when wielding with two hands."


class VitalStrike(Feat):
    name = 'Vital Strike'
    type = 'combat'
    _prerequisites = ['BAB 6']
    description = "Deal twice the normal damage on a single attack."


class ImprovedVitalStrike(Feat):
    name = 'Improved Vital Strike'
    type = 'combat'
    _prerequisites = ['Vital Strike', 'BAB 11']
    description = "Deal three times the normal damage on a single attack."


class GreaterVitalStrike(Feat):
    name = "Greater Vital Strike"
    type = 'combat'
    _prerequisites = ['Improved Vital Strike', 'BAB 16']
    description = "Deal four times the normal damage on a single attack."


class WeaponFinesse(Feat):
    name = "Weapon Finesse"
    type = 'combat'
    description = "Use DEX instead of STR on attack rolls with light weapons."
    modifiers = modifiers(
        #"+max(STR mod, DEX mod) - STR mod to melee damage modifier"
    )

    def respond_to_event(self, event, responses):
        # todo: Modify modifier for light weapons.
        pass


class WeaponFocus(Feat):
    name = "Weapon Focus"
    type = 'combat'
    description = 'You are particularly skilled with a chosen weapon.'
    _prerequisites = ['BAB 1']
    multiple = True
    # todo: dynamic list of weapon types.


class GreaterWeaponFocus(Feat):
    name = "Greater Weapon Focus"
    type = "combat"
    description = "You have great skill with a chosen weapon."
    _prerequisites = ['Weapon Focus (same subtype)', "8th-level Fighter"]


class PenetratingStrike(Feat):
    name = "Penetrating Strike"
    type = 'combat'
    _prerequisites = ['Weapon Focus', "12th-level Fighter"]
    description = "Your attacks ignore 5 points of damage reduction."


class GreaterPenetratingStrike(Feat):
    name = "Greater Penetrating Strike"
    type = 'combat'
    _prerequisites = ['Penetrating Strike', '16th-level Fighter']
    description = "Your attacks ignore 10 points of damage reduction."


class WeaponSpecialization(Feat):
    name = "Weapon Specialization"
    type = 'combat'
    description = "You are skilled at dealing damage with a chosen weapon."
    multiple = True
    _prerequisites = ['Weapon Focus (same subtype)', '4th-level Fighter']
    # todo: Weapon type subtypes.


class GreaterWeaponSpecialization(Feat):
    name = "Greater Weapon Specialization"
    type = 'combat'
    description = "You are skilled at devastating with a chosen weapon."
    multiple = True
    _prerequisites = ['Weapon Specialization (same subtype)',
                      'Greater Weapon Focus (same subtype)',
                      '12th-level Fighter']
    # todo: Weapon type subtypes.
