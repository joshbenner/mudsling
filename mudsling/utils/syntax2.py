from pyparsing import *

__all__ = ['Syntax', 'SyntaxParseError']


class MissingParameter(ParseException):
    pass


class SyntaxLiteral(object):
    def __init__(self, tok):
        self.text = tok[0].strip()

    def __repr__(self):
        return 'Literal("%s")' % self.text

    def parser(self, nextToken):
        return Literal(self.text)


class SyntaxParam(object):
    def __init__(self, tok):
        self.name = tok[1]

    def __repr__(self):
        return '<%s>' % self.name

    def result(self, loc, tok):
        return self.name, (tok[0].strip() or None), 'required', loc

    def parser(self, nextToken):
        terminate = nextToken if nextToken else StringEnd()
        parm = QuotedString('"') | SkipTo(terminate)
        parm.setParseAction(self.result)
        return parm


class SyntaxChoice(object):
    def __init__(self, tok):
        self.choices = tok[1]

    def __repr__(self):
        return '{%s}' % '|'.join(map(str, self.choices))

    def parser(self, nextToken):
        r = oneOf([x.text for x in self.choices])
        r.setParseAction(lambda l, t: ('__optset__', t[0], '', l))
        return r


class SyntaxOptional(object):
    def __init__(self, tok):
        self.inside = tok[1:-1]

    def __repr__(self):
        return 'Optional(%s)' % repr(self.inside)[1:-1]

    def parseAction(self, tok):
        for i, t in enumerate(tok):
            if isinstance(t, tuple):  # Make contained parameters optional.
                t = list(t)
                t[2] = 'optional'
                tok[i] = tuple(t)
        return tok

    def parser(self, nextToken):
        p = Optional(commandParser(self.inside, nextToken))
        p += FollowedBy(nextToken)
        p.setParseAction(self.parseAction)
        return p


def syntaxGrammar():
    """
    A parser for the syntax which describes command syntax.
    """
    syntax = Forward()

    literal = CharsNotIn('[]<>{}')
    literal.setParseAction(SyntaxLiteral)

    paramName = Regex(r"[^>]+")
    param = Literal('<') + paramName + Literal('>')
    param.setParseAction(SyntaxParam)

    orLiteral = CharsNotIn('[]<>{}|')
    orLiteral.setParseAction(SyntaxLiteral)
    orLiterals = Group(delimitedList(orLiteral, delim='|'))
    choice = Literal('{') + orLiterals + Literal('}')
    choice.setParseAction(SyntaxChoice)

    optional = Literal('[') + syntax + Literal(']')
    optional.setParseAction(SyntaxOptional)

    syntax << OneOrMore(param | choice | optional | literal)

    return syntax


def commandParser(syntaxTokens, nextToken=None):
    outTokens = []
    lastToken = nextToken or StringEnd()
    for i in range(len(syntaxTokens) - 1, -1, -1):
        token = syntaxTokens[i]
        lastToken = token.parser(lastToken)
        outTokens.append(lastToken)
    outTokens.reverse()
    return And(outTokens)


def parse(text, parser):
    parsed = {'argstr': text}
    optsets = 0
    all_tokens = parser.parseString(text, parseAll=True)
    value_tokens = (x for x in all_tokens if isinstance(x, tuple))
    for name, value, status, loc in value_tokens:
        if name == '__optset__':
            optsets += 1
            name = 'optset%d' % optsets
        elif status == 'required' and value is None:
            raise ParseException("Parameter %r is required" % name, loc=loc)
        parsed[name] = value
    return parsed


class Syntax(object):
    """
    Container object to conform to original Syntax API.
    """
    syntaxGrammar = syntaxGrammar()
    empty = False
    parser = None

    def __init__(self, syntax):
        self.natural = syntax.strip()
        if not self.natural:
            self.empty = True
        else:
            tokens = self.syntaxGrammar.parseString(syntax, parseAll=True)
            self.parser = commandParser(tokens)

    def parse(self, string):
        if self.empty:
            if not string.strip():
                return {'argstr': string}
            return False
        try:
            return parse(string, self.parser)
        except ParseException as e:
            self.err = e
            return False

# Confirm to Syntax API.
SyntaxParseError = ParseException

if __name__ == '__main__':
    import time
    ssp = syntaxGrammar()

    test = [
        ('<exitSpec> to <room>', [
            'In,i|Out,o to My New Room',
            '"Room to Delete"',  # Should error.
        ]),
        ('look [[at] <something>]', [
            'look',
            'look at that',
            'look "at another thing"',
            ]),
        ('<class> {named|called|=} <names>', [
            'thing called Foo',
            'another thing named Foo Too'
        ]),
        ('<newRoomName>', [
            'My New Room'
        ]),
        ('<something> [to <somewhere>]', [
            'me',
            'me to there',
            'to',
            ]),
        ('<foo> [to <bar>] as <baz>', [
            'foo to bar as baz',
            'foo as baz',
            ]),
        ('[<foo>] for <bar>', [
            'for bar',
            'foo for bar',
            ])
    ]

    for spec, tests in test:
        syntax = Syntax(spec)
        print spec, '->', repr(syntax.parser)
        for t in tests:
            #noinspection PyUnresolvedReferences
            start = time.clock()
            r = syntax.parse(t)
            #noinspection PyUnresolvedReferences
            duration = (time.clock() - start) * 1000
            print '  ', t, '->', r
            if not r:
                print '    ERROR:', syntax.err
            print '  (%.3fms)\n' % duration
