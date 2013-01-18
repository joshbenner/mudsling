import shlex

from mudsling import commands


class ParsedInput(object):
    """
    Represents a parsed line of input from an object, probably a player (but
    not necessarily).

    This class just parses the input and structures it, it does not interpret
    the command, match objects, or perform any processing. That is left up to
    the caller.

    @ivar cmdstr: The string entered which matches against available commands.
    @ivar argstr: The rest of the input after the command.
    @ivar dobjstr: The direct object string.
    @ivar iobjstr: The indirect object string.
    @ivar prepstr: The preposition string.
    @ivar prep: The set from commands.prepositions containing the matched
                preposition.
    """

    #: @type: str
    cmdstr = None

    #: @type: str
    argstr = None

    #: @type: str
    dobjstr = None

    #: @type: str
    iobjstr = None

    #: @type: str
    prepstr = None

    #: @type: set
    prep = None

    def __init__(self, raw):
        """
        Parses input into data that can be used to match to a command.

        Uses MOO-style command syntax:

            command direct-object preposition indirect-object

        @param raw: The raw string to parse.
        @type raw: str

        @return:
        """
        words = shlex.split(raw)
        self.cmdstr = words[0]
        argwords = words[1:]
        self.argstr = ' '.join(argwords)
        #cmdstr, argstr = [part.strip() for part in raw.split(' ', 1)]
        #argwords = [part.strip for part in self.argstr.split(' ')]

        prepinfo = self.find_preposition(argwords)

        if prepinfo is not None:
            self.prep, prepidx = prepinfo
            self.prepstr = argwords[prepidx]
            self.dobjstr = ' '.join(argwords[:prepidx])
            self.iobjstr = ' '.join(argwords[prepidx + 1:])
        else:
            self.dobjstr = self.argstr

    def find_preposition(self, argwords):
        for prepset in commands.prepositions:
            for prepAlias in prepset:
                if prepAlias in argwords:
                    return prepset, argwords.index(prepAlias)
        return None
