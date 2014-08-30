from pyparsing import *

__all__ = ['Syntax', 'SyntaxParseError']


class MissingParameter(ParseException):
    pass


class SyntaxToken(object):
    __slots__ = ('_exprCache',)

    def expr(self, nextToken=None):
        # Call with a nextToken first, and subsequent calls include it.
        if not hasattr(self, '_exprCache'):
            self._exprCache = self._expr(nextToken)
        return self._exprCache.copy()

    def _expr(self, nextToken):
        raise NotImplemented

    def first_token(self):
        """
        Get the leading token in this token set. Usually, it's just self.
        """
        return self


class SyntaxEnd(SyntaxToken):
    __slots__ = ()

    def _expr(self, nextToken):
        return StringEnd()


class SyntaxLiteral(SyntaxToken):
    __slots__ = ('text',)

    def __init__(self, tok):
        self.text = tok[0].strip()

    def __repr__(self):
        return 'Literal("%s")' % self.text

    def _expr(self, nextToken):
        if self.text in printables and self.text not in alphanums:
            return CaselessLiteral(self.text)
        else:
            return CaselessKeyword(self.text)


class WhiteSpaceAssertion(SyntaxToken):
    def __repr__(self):
        return '(white space)'

    def _expr(self, nextToken):
        return White()


class SyntaxChoice(SyntaxToken):
    __slots__ = ('choices',)

    def __init__(self, tok):
        self.choices = tok[1]

    def __repr__(self):
        return '{%s}' % '|'.join(map(str, self.choices))

    def _expr(self, nextToken):
        r = oneOf([x.text for x in self.choices], caseless=True)
        r.setParseAction(lambda l, t: ('__optset__', t[0], '', l))
        return r


class SyntaxParam(SyntaxToken):
    __slots__ = ('name',)

    def __init__(self, tok):
        self.name = tok[1]

    def __repr__(self):
        return '<%s>' % self.name

    def result(self, loc, tok):
        return self.name, (tok[0].strip() or None), 'required', loc

    def _expr(self, nextToken):
        terminate = nextToken.expr() if nextToken else StringEnd()
        firstToken = nextToken.first_token() if nextToken else None
        if isinstance(firstToken, SyntaxParam):
            terminate = White() | StringEnd()
        parm = QuotedString('"') | SkipTo(terminate)
        parm.setParseAction(self.result)
        return parm


class SyntaxOptional(SyntaxToken):
    __slots__ = ('inside',)

    def __init__(self, tok):
        self.inside = tok[1:-1]

    def __repr__(self):
        return 'Optional(%s)' % repr(self.inside)[1:-1]

    def parse_action(self, tok):
        if not len(tok):
            # Child params do not process if there is nothing there, so we need
            # to manually parse empty inputs with them so the results include
            # the params' keys.
            for child in self.inside:
                if isinstance(child, SyntaxParam):
                    try:
                        tok.insert(len(tok), child.result(0, ('',)))
                    except Exception as e:
                        pass
        for i, t in enumerate(tok):
            if isinstance(t, tuple):  # Make contained parameters optional.
                t = list(t)
                t[2] = 'optional'
                tok[i] = tuple(t)
        return tok

    def _expr(self, nextToken):
        p = Optional(command_parser(self.inside, nextToken))
        p += FollowedBy(nextToken.expr())
        p.setParseAction(self.parse_action)
        return p

    def first_token(self):
        return self.inside[0] if len(self.inside) > 0 else None


def syntax_grammar():
    """
    A parser for the syntax which describes command syntax.
    """
    syntax = Forward()

    literal = CharsNotIn('[]<>{}')
    literal.setParseAction(SyntaxLiteral)

    assertWhiteSpace = CaselessLiteral(r'\w')
    assertWhiteSpace.setParseAction(WhiteSpaceAssertion)

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

    syntax << OneOrMore(assertWhiteSpace | param | choice | optional | literal)

    return syntax


def command_parser(syntaxTokens, nextToken=None):
    expressions = []
    nextToken = nextToken or SyntaxEnd()
    tokens = list(syntaxTokens)
    tokens.reverse()
    for token in tokens:
        expressions.append(token.expr(nextToken))
        nextToken = token
    expressions.reverse()
    return And(expressions)


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
    __slots__ = ('natural', 'empty', 'parser', 'err')

    syntaxGrammar = syntax_grammar()

    def __init__(self, syntax):
        self.natural = syntax.strip()
        if not self.natural:
            self.empty = True
            self.parser = None
        else:
            self.empty = False
            tokens = self.syntaxGrammar.parseString(syntax, parseAll=True)
            self.parser = command_parser(tokens)

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

# Conform to Syntax API.
SyntaxParseError = ParseException

if __name__ == '__main__':
    import time
    ssp = syntax_grammar()

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
            'to',  # Should error
        ]),
        ('<foo> [to <bar>] as <baz>', [
            'foo to bar as baz',
            'foo as baz',
            ]),
        ('[<foo>] for <bar>', [
            'for bar',
            'foo for bar',
            ]),
        ('<names> [<password>]', [
            'hesterly',
            'hesterly test',
            '"Mr. Hesterly" test',
            'hesterly,blah test',
            '"just a long name"',
            ]),
        ('<foo> [<bar> to] <baz>', [
            'foo bar to baz',
            'foo to baz',
            'foo baz',
            ]),
        ('for <duration>', [
            'for 1h',
            'forever',
            ]),
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
