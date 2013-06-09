from .features import Feature
from .data import ForceSlotsMetaclass


class Skill(Feature):
    """
    A skill.

    Skill instances represent the level of that skill possessed by a character.
    """
    # So we don't need to set slots on every single skill class.
    __metaclass__ = ForceSlotsMetaclass
    __slots__ = ('ranks',)
    name = ''
    ability = None
    untrained = False
    ac_penalty = False


class Acrobatics(Skill):
    name = 'Acrobatics'
    ability = 'Dex'
    untrained = True
    ac_penalty = True


class Appraise(Skill):
    name = 'Appraise'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class Bluff(Skill):
    name = 'Bluff'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class Climb(Skill):
    name = 'Climb'
    ability = 'Str'
    untrained = True
    ac_penalty = True


class Craft(Skill):
    name = 'Craft'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class Diplomacy(Skill):
    name = 'Diplomacy'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class DisableDevice(Skill):
    name = 'Disable Device'
    ability = 'Dex'
    untrained = False
    ac_penalty = True


class Disguise(Skill):
    name = 'Disguise'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class EscapeArtist(Skill):
    name = 'Escape Artist'
    ability = 'Dex'
    untrained = True
    ac_penalty = True


class Fly(Skill):
    name = 'Fly'
    ability = 'Dex'
    untrained = True
    ac_penalty = True


class HandleAnimal(Skill):
    name = 'Handle Animal'
    ability = 'Cha'
    untrained = False
    ac_penalty = False


class Heal(Skill):
    name = 'Heal'
    ability = 'Wis'
    untrained = True
    ac_penalty = False


class Intimidate(Skill):
    name = 'Intimidate'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class KnowledgeArcana(Skill):
    name = 'Knowledge (arcana)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeDungeoneering(Skill):
    name = 'Knowledge (dungeoneering)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeEngineering(Skill):
    name = 'Knowledge (engineering)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeGeography(Skill):
    name = 'Knowledge (geography)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeHistory(Skill):
    name = 'Knowledge (history)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeLocal(Skill):
    name = 'Knowledge (local)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeNature(Skill):
    name = 'Knowledge (nature)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeNobility(Skill):
    name = 'Knowledge (nobility)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgePlanes(Skill):
    name = 'Knowledge (planes)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class KnowledgeReligion(Skill):
    name = 'Knowledge (religion)'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class Linguistics(Skill):
    name = 'Linguistics'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class Perception(Skill):
    name = 'Perception'
    ability = 'Wis'
    untrained = True
    ac_penalty = False


class Perform(Skill):
    name = 'Perform'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class Profession(Skill):
    name = 'Profession'
    ability = 'Wis'
    untrained = False
    ac_penalty = False


class Ride(Skill):
    name = 'Ride'
    ability = 'Dex'
    untrained = True
    ac_penalty = True


class SenseMotive(Skill):
    name = 'Sense Motive'
    ability = 'Wis'
    untrained = True
    ac_penalty = False


class SleightOfHand(Skill):
    name = 'Sleight of Hand'
    ability = 'Dex'
    untrained = False
    ac_penalty = True


class Spellcraft(Skill):
    name = 'Spellcraft'
    ability = 'Int'
    untrained = False
    ac_penalty = False


class Stealth(Skill):
    name = 'Stealth'
    ability = 'Dex'
    untrained = True
    ac_penalty = True


class Survival(Skill):
    name = 'Survival'
    ability = 'Wis'
    untrained = True
    ac_penalty = False


class Swim(Skill):
    name = 'Swim'
    ability = 'Str'
    untrained = True
    ac_penalty = True


class UseMagicDevice(Skill):
    name = 'Use Magic Device'
    ability = 'Cha'
    untrained = False
    ac_penalty = False
