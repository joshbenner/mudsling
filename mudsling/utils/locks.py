from pyparsing import Suppress, Literal, CaselessLiteral, Word, Group,\
    ZeroOrMore, alphanums, alphas, delimitedList, operatorPrecedence, opAssoc

opMap = {
    '!': 'not',
    '&': 'and',
    '|': 'or'
}


def LockParser(funcMap):
    funcs = {
        'not': lambda x: not x,
        'or': lambda l, r: l or r,
        'and': lambda l, r: l and r
    }
    funcs.update(funcMap)

    class LockFunc(object):
        def __init__(self, tok):
            self.fname, self.args = tok
            if self.fname in opMap:
                self.fname = opMap[self.fname]

        def __repr__(self):
            return '%s(%s)' % (self.fname, str(self.args)[1:-1])

        def eval(self):
            if self.fname in funcs:
                args = []
                for a in self.args:
                    if isinstance(a, LockFunc):
                        args.append(a.eval())
                    else:
                        args.append(a)
                return funcs[self.fname](*args)
            else:
                raise NameError("Invalid lock function: %s" % self.fname)

    def unaryOp(tok):
        op, rhs = tok[0]
        return LockFunc((op, [rhs]))

    def binaryOp(tok):
        lhs, op, rhs = tok[0]
        return LockFunc((op, [lhs, rhs]))

    lpar = Suppress('(')
    rpar = Suppress(')')

    opAnd = CaselessLiteral('and') | Literal('&')
    opOr = CaselessLiteral('or') | Literal('|')
    opNot = CaselessLiteral('not') | Literal('!')

    arg = Word(alphanums + r' #$%&*+-./:<=>?@[\]^_`{|}~')
    args = Group(ZeroOrMore(delimitedList(arg)))
    fname = Word(alphas, alphanums + '_')
    func = fname + lpar + args + rpar
    func.setParseAction(LockFunc)

    boolExpr = operatorPrecedence(
        func,
        [
            (opNot, 1, opAssoc.RIGHT, unaryOp),
            (opOr, 2, opAssoc.LEFT, binaryOp),
            (opAnd, 2, opAssoc.LEFT, binaryOp),
        ]
    )
    _grammar = boolExpr | func
    return _grammar


if __name__ == '__main__':
    import time
    test = [
        'very_strong()',
        'id(42)',
        'not dead()',
        'id(42) and not dead()',
        'has_perm(use things) or is_superuser()',
        'invalid_func()'
    ]
    funcMap = {
        'very_strong': lambda: True,
        'id': lambda id: int(id) == 42,
        'dead': lambda: False,
        'has_perm': lambda p: p in ['do stuff'],
        'is_superuser': lambda: True,
    }
    _grammar = LockParser(funcMap)
    for t in test:
        print t
        start = time.clock()
        try:
            r = _grammar.parseString(t)[0]
        except Exception as e:
            r = e
        duration = time.clock() - start
        print "parsed: ", r
        print "time: ", duration * 1000
        try:
            v = r.eval()
        except Exception as e:
            v = repr(e)
        print ' val = ', v, '\n'
