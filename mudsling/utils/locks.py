"""
Implements a generic pyparsing lock parser grammar.

Syntax for a lock: [NOT] func1(args) [AND|OR] [NOT] func2() [...]

Lock syntax involves functions, operators, and parentheses.
* Functions take the form of: <funcName>([<arg1>[, ...]])
* Binary (two-side) operators: and, or
* Unary (one-side) operators: not
* Parentheses can be used to logically group operations.

Examples:

    foo()
    foo() and bar(1)
    (foo() and bar(1)) or baz(a, b)

Syntax based on Evennia's lock system.
"""

from pyparsing import Suppress, Literal, CaselessLiteral, Word, Group,\
    ZeroOrMore, alphanums, alphas, delimitedList, operatorPrecedence, opAssoc

# Can be imported from this module by other modules, do not remove.
from pyparsing import ParseException
from mudsling.storage import PersistentSlots

# Alias symbols to their built-in functions. Used in LockParser().
opMap = {
    '!': 'not',
    '&': 'and',
    '|': 'or'
}


class LockFunc(PersistentSlots):
    """
    Generic form of a lock function. A child class using the specified function
    map will be dynamically created when a new L{LockParser} is created.
    """
    __slots__ = ('fname', 'args')

    def eval(self, *args):
        """
        Evaluate the lock and return the result. The position args will be
        passed to the lock function (and on to any functions it contains) at
        the front of parameter list.

        @param args: Position arguments to prepend to argument lists.
        @type args: C{tuple}

        @return: The result of evaluating the LockFunc.
        @rtype: bool
        """
        return False


# Mimics class naming since it is essentially a dynamic class instantiation.
def LockParser(funcMap):
    """
    Generate a lock parsing expression tree.

    @param funcMap: Dictionary of in-script function names to their Python
        functions.
    @rtype funcMap: C{dict}

    @return: An expression tree which can be evaluated.
    @rtype: L{pyparsing.ParserElement}
    """
    funcs = {
        'not': lambda _, __, x: not x,
        'or': lambda _, __, l, r: l or r,
        'and': lambda _, __, l, r: l and r
    }
    funcs.update(funcMap)

    class _lockFunc(LockFunc):
        def __init__(self, tok):
            self.fname, self.args = tok
            if self.fname in opMap:
                self.fname = opMap[self.fname]

        def __repr__(self):
            return '%s(%s)' % (self.fname, str(self.args)[1:-1])

        def eval(self, *args):
            if self.fname in funcs:
                myArgs = list(args)
                for a in self.args:
                    if isinstance(a, _lockFunc):
                        myArgs.append(a.eval(*args))
                    else:
                        myArgs.append(a)
                return funcs[self.fname](*myArgs)
            else:
                raise NameError("Invalid lock function: %s" % self.fname)

    def unary_op(tok):
        op, rhs = tok[0]
        return _lockFunc((op, [rhs]))

    def binary_op(tok):
        lhs, op, rhs = tok[0]
        return _lockFunc((op, [lhs, rhs]))

    opAnd = CaselessLiteral('and') | Literal('&')
    opOr = CaselessLiteral('or') | Literal('|')
    opNot = CaselessLiteral('not') | Literal('!')

    arg = Word(alphanums + r' #$%&*+-./:<=>?@[\]^_`{|}~')
    args = Group(ZeroOrMore(delimitedList(arg)))

    fname = Word(alphas, alphanums + '_')
    func = fname + Suppress('(') + args + Suppress(')')
    func.setParseAction(_lockFunc)

    # noinspection PyUnresolvedReferences
    expr = operatorPrecedence(
        func,
        [
            (opNot, 1, opAssoc.RIGHT, unary_op),
            (opOr, 2, opAssoc.LEFT, binary_op),
            (opAnd, 2, opAssoc.LEFT, binary_op),
        ]
    )
    return expr


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
        except ParseException as e:
            r = e
        duration = time.clock() - start
        print "parsed: ", r
        print "time: ", duration * 1000
        try:
            v = r.eval()
        except Exception as e:
            v = repr(e)
        print ' val = ', v, '\n'
