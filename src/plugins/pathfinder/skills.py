import pathfinder.features


class Skill(pathfinder.features.Feature):
    """
    A skill.

    Skills are not instantiated.
    """
    name = ''
    ability = None
    untrained = False
    ac_penalty = False


# Skills are classes instead of instances so we can keep things consistent, and
# so we don't have to get very creative with how references to code-based data
# are stored.
