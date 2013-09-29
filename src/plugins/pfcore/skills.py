from pathfinder.skills import Skill


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


class CraftArmor(Skill):
    name = 'Craft (armor)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftBaskets(Skill):
    name = 'Craft (baskets)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftBooks(Skill):
    name = 'Craft (books)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftBows(Skill):
    name = 'Craft (bows)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftCalligraphy(Skill):
    name = 'Craft (calligraphy)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftCarpentry(Skill):
    name = 'Craft (carpentry)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftCloth(Skill):
    name = 'Craft (cloth)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftClothing(Skill):
    name = 'Craft (clothing)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftGlass(Skill):
    name = 'Craft (glass)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftJewelry(Skill):
    name = 'Craft (jewelry)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftLeather(Skill):
    name = 'Craft (leather)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftLocks(Skill):
    name = 'Craft (locks)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftPaintings(Skill):
    name = 'Craft (paintings)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftPottery(Skill):
    name = 'Craft (pottery)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftSculptures(Skill):
    name = 'Craft (sculptures)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftShips(Skill):
    name = 'Craft (ships)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftStonemasonry(Skill):
    name = 'Craft (stonemasonry)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftTraps(Skill):
    name = 'Craft (traps)'
    ability = 'Int'
    untrained = True
    ac_penalty = False


class CraftWeapons(Skill):
    name = 'Craft (weapons)'
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


# class Fly(Skill):
#     name = 'Fly'
#     ability = 'Dex'
#     untrained = True
#     ac_penalty = True


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


# class KnowledgeArcana(Skill):
#     name = 'Knowledge (arcana)'
#     ability = 'Int'
#     untrained = False
#     ac_penalty = False


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


# class KnowledgeNobility(Skill):
#     name = 'Knowledge (nobility)'
#     ability = 'Int'
#     untrained = False
#     ac_penalty = False


# class KnowledgePlanes(Skill):
#     name = 'Knowledge (planes)'
#     ability = 'Int'
#     untrained = False
#     ac_penalty = False


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


class PerformActing(Skill):
    name = 'Perform (acting)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformComedy(Skill):
    name = 'Perform (comedy)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformDance(Skill):
    name = 'Perform (dance)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformKeyboard(Skill):
    name = 'Perform (keyboard instruments)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformOratory(Skill):
    name = 'Perform (oratory)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformPercussion(Skill):
    name = 'Perform (percussion instruments)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformString(Skill):
    name = 'Perform (string instruments)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformWind(Skill):
    name = 'Perform (wind instruments)'
    ability = 'Cha'
    untrained = True
    ac_penalty = False


class PerformSing(Skill):
    name = 'Perform (sing)'
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


# class Spellcraft(Skill):
#     name = 'Spellcraft'
#     ability = 'Int'
#     untrained = False
#     ac_penalty = False


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


# class UseMagicDevice(Skill):
#     name = 'Use Magic Device'
#     ability = 'Cha'
#     untrained = False
#     ac_penalty = False
