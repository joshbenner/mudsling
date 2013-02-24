

def parse_names(input):
    """
    Parse user input into a list of string aliases.
    @rtype: list
    """
    names = filter(lambda x: x, map(str.strip, input.split(',')))
    if not len(names):
        raise Exception("Invalid name spec")
    return names
