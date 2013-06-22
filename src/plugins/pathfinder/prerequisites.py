"""
Prerequisites are stats and feature requirements.

Syntax: [not] <stat> <minimum>
    or: [not] <type> feat slot
    or: [not] <feature> [(<subtype>)]
    or: [not] <N><ord>-level <class>
    or: [not] restricted

Examples:
* restricted
* BAB 6
* Combat Expertise
* Weapon Focus (Shortsword)
* 9th-level Fighter
"""
import re

slot_re = re.compile(r'^(?P<type>.*) +feat +slot$')
lvl_re = re.compile(r'^(?P<level>\d+)(?:st|th|rd)-level +(?P<class>.*)$')
stat_re = re.compile(r'^(?P<stat>.*) +(?P<minimum>\d+)$')
feature_re = re.compile('^(?P<name>.*?)(?: +\((?P<subtype>.*)\))?$')


def check(prerequisites, character):
    """
    Determine if the character satisfies the prerequisites.

    @param prerequisites: List of prerequisite expressions.
    @type prerequisites: C{list} or C{tuple} or C{set}
    @param character: The character to test for compliance.
    @type character: L{pathfinder.Character}

    @rtype: C{bool}
    """
    for pr in prerequisites:
        if not check_prerequisite(pr, character):
            return False
    return True


def check_prerequisite(prerequisite, character):
    """
    Determine if the character satisfies a single prerequisite expression.

    @param prerequisite: List of prerequisite expressions.
    @type prerequisite: C{str}
    @param character: The character to test for compliance.
    @type character: L{pathfinder.Character}

    @rtype: C{bool}
    """
    if prerequisite.startswith('not '):
        return not check_prerequisite(prerequisite[4:], character)
    if prerequisite == 'restricted':
        return False
    m = slot_re.match(prerequisite)
    if m:
        available_slots = character.available_feat_slots()
        slot_type = m.groupdict()['type']
        return slot_type in available_slots and available_slots[slot_type] > 0
    m = lvl_re.match(prerequisite)
    if m:
        level, class_name = m.groups()
        class_name = class_name.lower()
        level = int(level)
        for cls, lvl in character.classes:
            if cls.name.lower() == class_name:
                return lvl >= level
        return False
    m = stat_re.match(prerequisite)
    if m:
        stat, minimum = m.groups()
        try:
            return character.get_stat(stat) >= int(minimum)
        except KeyError:
            return False
    m = feature_re.match(prerequisite)
    if m:
        name, subtype = m.groups()
        return character.has_feature(name, subtype)
