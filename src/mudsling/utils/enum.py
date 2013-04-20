

def enum(*sequential, **named):
    """
    Generate an enum in python.

    >>> myEnum = enum(A=0, B=1, C=2)
    >>> myEnum.A == 0
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)
