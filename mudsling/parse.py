from mudsling import commands


def parse_input(raw):
    """
    Parses input into data that can be used to match to a command.

    Uses MOO-style command syntax:

        command direct-object preposition indirect-object

    @param raw: The raw string to parse.
    @type raw: str

    @return:
    """
    cmdstr, argstr = [part.strip() for part in raw.split(' ', 1)]
    argwords = [part.strip for part in argstr.split(' ')]

    prepidx = find_preposition(argwords)

    if prepidx is not None:
        dobjstr = argwords[:prepidx]
        iobjstr = argwords[prepidx + 1:]
    else:
        dobjstr = argstr
        iobjstr = None


def find_preposition(argwords):
    for prepset in commands.prepositions:
        for prepAlias in prepset:
            if prepAlias in argwords:
                return argwords.index(prepAlias)
    return None
