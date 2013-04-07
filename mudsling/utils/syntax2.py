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

    def result(self, s, loc, tok):
        val = tok[0].strip()
        if not val:
            msg = "%r parameter is required" % self.name
            raise MissingParameter(s, loc=loc, msg=msg)
        return self.name, val

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
        r.setParseAction(lambda t: ('__optset__', t[0]))
        return r


class SyntaxOptional(object):
    def __init__(self, tok):
        self.inside = tok[1:-1]

    def __repr__(self):
        return 'Optional(%s)' % repr(self.inside)[1:-1]

    def failAction(self, s, loc, expr, err):
        t = s

    def parser(self, nextToken):
        p = Optional(commandParser(self.inside))
        p.setFailAction(self.failAction)
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


def commandParser(syntaxTokens):
    outTokens = []
    length = len(syntaxTokens)
    for i in range(0, length):
        token = syntaxTokens[i]
        next = syntaxTokens[i + 1] if i < length - 1 else None
        outToken = token.parser(next.parser(None) if next else None)
        outTokens.append(outToken)
    return And(outTokens)


def parse(text, parser):
    parsed = {'argstr': text}
    optsets = 0
    for token in (x for x in parser.parseString(text, parseAll=True)
                  if isinstance(x, tuple)):
        if token[0] == '__optset__':
            optsets += 1
            parsed['optset%d' % optsets] = token[1]
        else:
            parsed[token[0]] = token[1]
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
        except ParseException:
            return False

# Confirm to Syntax API.
SyntaxParseError = ParseException

if __name__ == '__main__':
    import time
    ssp = syntaxGrammar()

    test = {
        '<exitSpec> to <room>': [
            'In,i|Out,o to My New Room',
            '"Room to Delete"',  # Should error.
        ],
        'look [[at] <something>]': [
            'look',
            'look at that',
            'look "at another thing"',
        ],
        '<class> {named|called|=} <names>': [
            'thing called Foo',
            'another thing named Foo Too'
        ],
        '<newRoomName>': [
            'My New Room'
        ],
    }

    for spec, tests in test.iteritems():
        syntax = Syntax(spec)
        print spec, '->', repr(syntax.parser)
        for t in tests:
            #noinspection PyUnresolvedReferences
            start = time.clock()
            r = syntax.parse(t)
            #noinspection PyUnresolvedReferences
            duration = (time.clock() - start) * 1000
            print '  ', t, '->', r
            print '  (%.3fms)' % duration
