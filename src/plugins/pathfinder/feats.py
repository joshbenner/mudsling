from .features import Feature
from .data import ForceSlotsMetaclass
from .effects import effects


class Feat(Feature):
    """
    A feat.

    Instances represent the possession of the feat. So, when a character gains
    a feat, an instance of that feat is stored on the character. This allows
    some feats to have feat subtypes (ie: which weapon for Weapon Focus).
    """
    __metaclass__ = ForceSlotsMetaclass
    __slots__ = ('subtype',)
    name = ''
    type = 'general'
    multiple = False
    subtypes = []
    prerequisites = []
    effects = []


class Acrobatic(Feat):
    name = 'Acrobatic'
    effects = effects(
        '+2 bonus on Acrobatics checks',
        '+2 bonus on Fly checks'
    )


class AgileManeuvers(Feat):
    name = 'Agile Maneuvers'
    type = 'combat'
    effects = effects(
        'CMB = BAB + max(STR, DEX) - Size mod'
    )


class Altertness(Feat):
    name = 'Alertness'
    effects = effects(
        '+2 bonus on Perception checks',
        '+2 bonus on SEnse Motive checks'
    )


class AlignmentChannel(Feat):
    name = 'Alignment Channel'
    prerequisites = ["Channel Energy"]
    multiple = True
    subtypes = ['chas', 'evil', 'good', 'law']


class AnimalAffinity(Feat):
    name = 'Animal Affinity'
    effects = effects(
        '+2 bonus on Handle Animal checks',
        '+2 bonus on Ride checks'
    )


class ArcaneArmorTraining(Feat):
    name = 'Arcane Armor Training'
    type = 'combat'
    prerequisites = [
        'Armor Proficiency, Light',
        'caster level 3rd'
    ]
    effects = effects('-10% to arcane spell failure chance')


class ArcaneArmorMastery(Feat):
    name = 'Arcane Armor Mastery'
    type = 'combat'
    prerequisites = [
        'Arcane Armor Training',
        'Armor Proficiency, Medium',
        'caster level 7th'
    ]
    effects = effects('-10% to arcane spell failure chance')


class ArcaneStrike(Feat):
    name = 'Arcane Strike'
    prerequisites = ['Cast arcane spells']


class ArmorProficiencyLight(Feat):
    name = 'Armor Proficiency, Light'


class ArmorProficiencyMedium(Feat):
    name = 'Armor Proficiency, Medium'
    prerequisites = ['Armor Proficiency, Light']


class ArmorProficiencyHeavy(Feat):
    name = 'Armor Proficiency, Heavy'
    prerequisites = ['Armor Proficiency, Medium']


class Athletic(Feat):
    name = 'Athletic'
    effects = effects(
        '+2 bonus on Climb checks',
        '+2 bonus on Swim checks'
    )


class AugmentSummoning(Feat):
    name = 'Augment Summoning'
    prerequisites = ['Spell Focus (conjuration)']


class BlindFight(Feat):
    name = 'Blind-Fight'
    type = 'combat'
    effects = effects('Concealment miss chance = 10%')


class CatchOffGuard(Feat):
    name = "Catch Off-Guard"
    type = 'combat'
    effects = effects('Improvised weapon penalty = 0')


class ChannelSmite(Feat):
    name = 'Channel Smite'
    type = 'combat'
    prerequisites = ['Channel Energy']


class CombatCasting(Feat):
    name = 'Combat Casting'
    effects = effects('+4 bonus to Concentration checks to cast defensively')


class CombatExpertise(Feat):
    name = 'Combat Expertise'
    type = 'combat'
    prerequisites = ['Intelligence 13']


class ImprovedDisarm(Feat):
    name = 'Improved Disarm'
    type = 'combat'
    prerequisites = ['Combat Expertise']
    effects = effects('+2 bonus on disarm attempts')


class GreaterDisarm(Feat):
    name = 'Greater Disarm'
    type = 'combat'
    prerequisites = [
        'Improved Disarm',
        'BAB 6'
    ]
    effects = effects('+4 bonus on disarm attempts')


class ImprovedFeint(Feat):
    name = 'Improved Feint'
    type = 'combat'
    prerequisites = ['Combat Expertise']


class GreaterFeint(Feat):
    name = 'Greater Feint'
    type = 'combat'
    prerequisites = [
        'Improved Feint',
        'BAB 6'
    ]


class ImprovedTrip(Feat):
    name = 'Improved Trip'
    type = 'combat'
    prerequisites = ['Combat Expertise']


class GreaterTrip(Feat):
    name = 'Greater Trip'
    type = 'combat'
    prerequisites = [
        'Improved Trip',
        'BAB 6'
    ]


class WhirlwindAttack(Feat):
    name = 'Whirlwind Attack'
    type = 'combat'
    prerequisites = [
        'Dexterity 13',
        'Combat Expertise',
        'Sprint Attack',
        'BAB 4'
    ]


class CombatReflexes(Feat):
    name = 'Combat Reflexes'
    type = 'combat'
    prerequisites = ['BAB 9']


class CriticalFocus(Feat):
    name = 'Critical Focus'
    type = 'combat'
    prerequisites = ['BAB 9']
    effects = effects('+4 bonus to critical confirmation')


class DeadlyAim(Feat):
    name = 'Deadly Aim'
    type = 'combat'
    prerequisites = [
        'Dexterity 13',
        'BAB 1'
    ]


class Deceitful(Feat):
    name = 'Deceitful'
    effects = effects(
        '+2 bonus on Bluff checks',
        '+2 bonus to Disguise checks'
    )


class DefensiveCombatTraining(Feat):
    name = 'Defensive Combat Training'
    type = 'combat'
    effects = effects(
        'CMD = 10 + max(BAB, HD) + STR + DEX - Size mod'
    )


class DeftHands(Feat):
    name = 'Deft Hands'
    effects = effects(
        '+2 bonus on Disable Device checks',
        '+2 bonus on Sleight of Hand checks'
    )


class Disruptive(Feat):
    name = 'Disruptive'
    type = 'combat'
    prerequisites = ['6th-level Fighter']


class Spellbreaker(Feat):
    name = 'Spellbreaker'
    type = 'combat'
    prerequisites = ['Disruptive', '10th-level Fighter']


class Dodge(Feat):
    name = 'Dodge'
    type = 'combat'
    prerequisites = ['Dexterity 13']
    effects = effects('+1 dodge bonus to AC')


class Mobility(Feat):
    name = 'Mobility'
    type = 'combat'
    prerequisites = ['Dodge']
    effects = effects('+4 AC against attacks of opportunity from movement')


class SpringAttack(Feat):
    name = 'Spring Attack'
    type = 'combat'
    prerequisites = ['Mobility', 'BAB 4']


class ElementalChannel(Feat):
    name = 'Elemental Channel'
    prerequisites = ['Channel Energy']


class Endurance(Feat):
    name = 'Endurance'


class Diehard(Feat):
    name = 'Diehard'
    prerequisites = ['Endurance']


class EschewMaterials(Feat):
    name = 'Eschew Materials'


class ExoticWeaponProficiency(Feat):
    name = 'Exotic Weapon Proficiency'
    type = 'combat'
    prerequisites = ['BAB 1']


class ExtraChannel(Feat):
    name = 'Extra Channel'
    prerequisites = ['Channel Energy']
    effects = effects("+2 channel energy uses")


class ExtraKi(Feat):
    name = 'Extra Ki'
    prerequisites = ['Ki Pool']
    effects = effects("+2 ki pool")


class ExtraLayOnHands(Feat):
    name = 'Extra Lay On Hands'
    prerequisites = ['Lay On Hands']
    effects = effects("+2 lay on hands uses")


class FatiguedMercy(Feat):
    name = "Fatigued Mercy"
    type = 'mercy'
    prerequisites = ['3rd-level Paladin']


class ShakenMercy(Feat):
    name = "Shaken Mercy"
    type = 'mercy'
    prerequisites = ['3rd-level Paladin']


class SickenedMercy(Feat):
    name = 'Sickened Mercy'
    type = 'mercy'
    prerequisites = ['3rd-level Paladin']


class DazedMercy(Feat):
    name = 'Dazed Mercy'
    type = 'mercy'
    prerequisites = ['6th-level Paladin']


class DiseasedMercy(Feat):
    name = 'Diseased Mercy'
    type = 'mercy'
    prerequisites = ['6th-level Paladin']


class StaggeredMercy(Feat):
    name = 'Staggered Mercy'
    type = 'mercy'
    prerequisites = ['6th-level Paladin']


class CursedMercy(Feat):
    name = 'Cursed Mercy'
    type = 'mercy'
    prerequisites = ['9th-level Paladin']


class ExhaustedMercy(Feat):
    name = 'Exhausted Mercy'
    type = 'mercy'
    prerequisites = ['9th-level Paladin']


class FrightenedMercy(Feat):
    name = 'Frightened Mercy'
    type = 'mercy'
    prerequisites = ['9th-level Paladin']


class NauseatedMercy(Feat):
    name = 'Nauseated Mercy'
    type = 'mercy'
    prerequisites = ['9th-level Paladin']


class PoisonedMercy(Feat):
    name = 'Poisoned Mercy'
    type = 'mercy'
    prerequisites = ['9th-level Paladin']


class BlindedMercy(Feat):
    name = 'Blinded Mercy'
    type = 'mercy'
    prerequisites = ['12th-level Paladin']


class DeafenedMercy(Feat):
    name = 'Deafened Mercy'
    type = 'mercy'
    prerequisites = ['12th-level Paladin']


class ParalyzedMercy(Feat):
    name = 'Paralyzed Mercy'
    type = 'mercy'
    prerequisites = ['12th-level Paladin']


class StunnedMercy(Feat):
    name = 'Stunned Mercy'
    type = 'mercy'
    prerequisites = ['12th-level Paladin']


class ExtraPerformance(Feat):
    name = "Extra Performance"
    prerequisites = ['Bardic Performance']
    effects = effects('+6 rounds of bardic performance')


class ExtraRage(Feat):
    name = "Extra Rage"
    prerequisites = ['Rage']
    effects = effects('+6 rounds of rage')


class GreatFortitude(Feat):
    name = "Great Fortitude"
    effects = effects('+2 on Fortitude saves')


class ImprovedGreatFortitude(Feat):
    name = "Improved Great Fortitude"
    prerequisites = ['Great Fortitude']
    effects = effects('+2 on Fortitude saves')


class ImprovedChannel(Feat):
    name = "Improved Channel"
    prerequisites = ['Channel Energy']
    effects = effects('+2 to channel energy DC')


class ImprovedCounterspell(Feat):
    name = "Improved Counterspell"


class ImprovedCritical(Feat):
    name = 'Improved Critical'
    type = 'combat'
    prerequisites = ['BAB 8']
    multiple = True
    subtypes = ()  # todo: Dynamically load weapon types


class ImprovedInitiative(Feat):
    name = "Improved Initiative"
    type = "combat"
    effects = effects('+4 bonus to initiative')


class ImprovedUnarmedStrike(Feat):
    name = "Improved Unarmed Strike"
    type = "combat"
    effects = effects('Lethal unarmed strike = BAB + STR + Size mod')


class DeflectArrows(Feat):
    name = "Deflect Arrows"
    type = "combat"
    prerequisites = ['Dexterity 13', 'Improved Unarmed Strike']


class SnatchArrows(Feat):
    name = "Snatch Arrows"
    type = "combat"
    prerequisites = ['Dexterity 15', 'Deflect Arrows']


class ImprovedGrapple(Feat):
    name = "Improved Grapple"
    type = "combat"
    prerequisites = ['Dexterity 13', 'Improved Unarmed Strike']
    effects = effects('+2 bonus on grapple attempts')


class GreaterGrapple(Feat):
    name = "Greater Grapple"
    type = "combat"
    prerequisites = ['BAB 6', 'Improved Grapple']
    effects = effects('+2 bonus on grapple attempts')


class ScorpionStyle(Feat):
    name = "Scorpion Style"
    type = "combat"
    prerequisites = ['Improved Unarmed Strike']


class FistOfGorgon(Feat):
    name = "Fist of Gorgon"
    type = "combat"
    prerequisites = ['Scorpion Style', 'BAB 6']


class WrathOfMedusa(Feat):
    name = "Wrath of Medusa"
    type = "combat"
    prerequisites = ['Fist of Gorgon', 'BAB 11']


class StunningFist(Feat):
    name = 'Stunning Fist'
    type = 'combat'
    prerequisites = ['Dexterity 13', 'Wisdom 13', 'Improved Unarmed Strike',
                     'BAB 8']


class ImprovisedWeaponMastery(Feat):
    name = 'Improvised Weapon Mastery'
    type = 'combat'
    prerequisites = ['Catch Off-Guard', 'BAB 8']
    effects = effects('+1d4 to improvised weapon damage')


class IntimidatingProwess(Feat):
    name = 'Intimidating Prowess'
    type = 'combat'
    effects = effects('+STR to Intimidate skill checks')


class IronWill(Feat):
    name = 'Iron Will'
    effects = effects('+2 bonus on Will saves')


class ImprovedIronWill(Feat):
    name = 'Improved Iron Will'
    prerequisites = ['Iron Will']
    effects = effects('+2 bonus on Will saves')


class LightningReflexes(Feat):
    name = 'Lightning Reflexes'
    effects = effects('+2 bonus on Reflex saves')


class ImprovedLightningReflexes(Feat):
    name = 'Improved Lightning Reflexes'
    prerequisites = ['Lightning Reflexes']
    effects = effects('+2 bonus on Reflex saves')


class Lunge(Feat):
    name = "Lunge"
    type = 'combat'
    prerequisites = ['BAB 6']


class MagicalAptitude(Feat):
    name = 'Magical Aptitude'
    effects = effects(
        '+2 bonus on Spellcraft checks',
        '+2 bonus on Use Magic Device checks'
    )


class MartialWeaponProficiency(Feat):
    name = 'Martial Weapon Proficiency'
    type = 'combat'
    multiple = True
    subtypes = ()  # todo: Dynamic martial weapon list


class Persuasive(Feat):
    name = 'Persuasive'
    effects = effects(
        '+2 bonus on Diplomacy checks',
        '+2 bonus on Intimidate checks'
    )


class PointBlankShot(Feat):
    name = 'Point-Blank Shot'


class FarShot(Feat):
    name = 'Far Shot'
    prerequisites = ['Point-Blank Shot']
    effects = effects('range increment penalty = 0')


class PreciseShot(Feat):
    name = 'Precise Shot'
    prerequisites = ['Point-Blank Shot']
    effects = effects('shoot into melee penalty = 0')


class ImprovedPreciseShot(Feat):
    name = 'Improved Precise Shot'
    prerequisites = ['Precise Shot', 'Dexterity 19', 'BAB 11']

