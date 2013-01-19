import shlex

from mudsling import commands


class ParsedInput(object):
    """
    Represents a parsed line of input from an object, probably a player (but
    not necessarily).

    @ivar actor: The object that issued the command, if any.
    @ivar raw: The raw input string.
    @ivar cmdstr: The string entered which matches against available commands.
    @ivar argstr: The rest of the input after the command.
    @ivar dobjstr: The direct object string.
    @ivar iobjstr: The indirect object string.
    @ivar prepstr: The preposition string.
    @ivar prep: The set from commands.prepositions containing the matched
                preposition.
    @ivar dobj: The single direct object match.
    @ivar iobj: The single indirect object match.
    @ivar dobj_matches: The search results for direct object.
    @ivar iobj_matches: The search results for indirect object.
    """

    #: @type: mudsling.objects.BaseObject
    actor = None

    #: @type: str
    raw = ""

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

    #: @type: mudsling.objects.BaseObject
    dobj = None

    #: @type: mudsling.objects.BaseObject
    iobj = None

    dobj_matches = set()
    iobj_matches = set()

    def __init__(self, raw, actor=None):
        """
        Parses input into data that can be used to match to a command.

        Uses MOO-style command syntax:

            command direct-object preposition indirect-object

        Will setup the various instance variables. However, if no actor is
        provided, then it will not do any object matching on the objSpecs.

        @param raw: The raw string to parse.
        @type raw: str

        @param actor: The object that issued the command, if any.
        @type actor: mudsling.objects.BaseObject
        """
        self.raw = raw
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

        if actor is not None:
            self.dobj_matches = actor.matchObject(self.dobjstr)
            self.iobj_matches = actor.matchObject(self.iobjstr)

            if len(self.dobj_matches) == 1:
                self.dobj = self.dobj_matches[0]
            if len(self.iobj_matches) == 1:
                self.iobj = self.iobj_matches[0]

    def find_preposition(self, argwords):
        for prepset in commands.prepositions:
            for prepAlias in prepset:
                if prepAlias in argwords:
                    return prepset, argwords.index(prepAlias)
        return None
