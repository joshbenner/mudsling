"""
Generic dice-rolling library based on pyparsing.

Extended BNF (same as Python specification):
     lowercase ::= "a"..."z"
     uppercase ::= "A"..."Z"
        letter ::= lowercase | uppercase
         digit ::= "0"..."9"
  alphanumeric ::= letter | digit
    identifier ::= (letter | "_") alphanumeric+
       integer ::= digit+
    fractional ::= digit* "." digit+
        number ::= integer | fractional
        seqnum ::= ["-"] (number | identifier)
      sequence ::= "{" seqnum ( ("," seqnum)* | (".." seqnum) ) "}"
          roll ::= [integer] "d" (integer | sequence)
       literal ::= roll | number
         group ::= "(" expression ")"
         unary ::= ("+" | "-") expression
      exponent ::= expression "^" expression
      multiply ::= expression "*" expression
        divide ::= expression "/" expression
           add ::= expression "+" expression
      subtract ::= expression "-" expression
       arglist ::= expression ("," expression)*
      function ::= identifier "(" [arglist] ")"
       seqexpr ::= (roll | sequence | function) "." function
          atom ::= function | seqexpr | identifier | literal | group
    expression ::= atom | unary | exponent | multiply | divide | add | subtract

Examples:
    2d10 -- Yields a sequence containing two rolls of a 10-sided die.
    1d20 + 5 -- Yields result of rolling a d20 and adding 5.
    d{2, 4, 6} -- Yields 2, 4, or 6 with equal probability.
    2d20.minSum(2) -- Yields the sequence whose sum is least of two 2d20 rolls.
    {STR, DEX}.max() -- Yields the greater of STR or DEX identifiers.
    ceil(d6 / 2) -- Yields the result of rolling a d6 rounded up.

Sequence Methods:
    .max() => Largest value in the sequence.
    .min() => Smallest value in the sequence.
    .sum() => Result of adding all sequence elements together.
    .highest(N) => Sequence containing greatest N elements.
    .lowest(N) => Sequence containing lowest N elements.

Functions:
    trunc
    floor
    ceil
    round
    min
    max
    sum

Notes:
* Adding a sequence to a number coerces the sequence to a sum of its elements.
"""
import math
import random


class EvalNode(object):
    def eval(self, vars=None):
        raise NotImplementedError()


class Sequence(EvalNode):
    data = []

    def __init__(self, lst=None):
        self.data = list(lst) if lst else []

    def _op(self, op, other, *args):
        if isinstance(other, int) or isinstance(other, float):
            return getattr(sum(self.data), op)(other, *args)

    __add__ = lambda self, x: self._op('__add__', x)
    __sub__ = lambda self, x: self._op('__sub__', x)
    __mul__ = lambda self, x: self._op('__mul__', x)
    __div__ = lambda self, x: self._op('__div__', x)
    __pow__ = lambda self, x, z=None: self._op('__pow__', x, z)

    __radd__ = lambda self, x: self._op('__add__', x)
    __rsub__ = lambda self, x: self._op('__rsub__', x)
    __rmul__ = lambda self, x: self._op('__rmul__', x)
    __rdiv__ = lambda self, x: self._op('__rdiv__', x)
    __rpow__ = lambda self, x, z=None: self._op('__rpow__', x, z)

    __neg__ = lambda self: -sum(*self.data)
    __pos__ = lambda self: sum(*self.data)
    __abs__ = lambda self: abs(sum(*self.data))
    __invert__ = lambda self: ~sum(*self.data)
    __index__ = lambda self: int(sum(*self.data))

    def __repr__(self):
        return "Sequence(%r)" % self.data


class DieRoll(EvalNode):
    def __init__(self, num_dice, sides):
        if isinstance(sides, basestring):
            sides = int(sides)
        self.num_dice = int(num_dice)
        self.sides = sides

    def __repr__(self):
        return "DieRoll(%r, %r)" % (self.num_dice, self.sides)

    def eval(self, vars=None):
        if isinstance(self.sides, list):
            return Sequence(random.choice(self.sides)
                            for _ in range(1, self.num_dice + 1))
        else:
            return Sequence(random.randint(1, self.sides + 1)
                            for _ in range(1, self.num_dice + 1))


def _grammar():
    import operator
    from pyparsing import alphas, alphanums, nums
    from pyparsing import oneOf, Suppress, Optional
    from pyparsing import Forward, operatorPrecedence, opAssoc, Word
    from pyparsing import delimitedList, Combine, Literal

    class LiteralNode(EvalNode):
        def __init__(self, tok):
            try:
                self.value = int(tok[0])
            except ValueError:
                self.value = float(tok[0])

        def eval(self, vars=None):
            return self.value

        def __repr__(self):
            return "Literal(%s)" % str(self.value)

    class VariableNode(EvalNode):
        def __init__(self, tok):
            self.name = tok[0]

        def eval(self, vars=None):
            if vars is not None and self.name in vars:
                return vars[self.name]
            print vars
            raise NameError("Variable '%s' not found" % self.name)

        def __repr__(self):
            return "$%s" % self.name

    class BinaryOpNode(EvalNode):
        ops = {
            '^': operator.pow,
            '*': operator.mul,
            '/': operator.div,
            '+': operator.add,
            '-': operator.sub,
        }

        def __init__(self, tok):
            self.lhs, self.op, self.rhs = tok[0]

        def __repr__(self):
            return "%s %s %s" % (self.lhs, self.op, self.rhs)

        def eval(self, vars=None):
            return self.ops[self.op](self.lhs.eval(vars), self.rhs.eval(vars))

    class UnaryOpNode(EvalNode):
        ops = {
            '-': operator.neg,
            '+': lambda x: x,
        }

        def __init__(self, tok):
            self.op, self.rhs = tok[0]

        def __repr__(self):
            return "%s%s" % (self.op, self.rhs)

        def eval(self, vars=None):
            return self.ops[self.op](self.rhs.eval(vars))

    class FunctionNode(VariableNode):
        def __init__(self, tok):
            super(FunctionNode, self).__init__(tok)
            self.args = tok[1:]

        def __repr__(self):
            return "%s(%s)" % (self.name, ', '.join(map(repr, self.args)))

        def eval(self, vars=None):
            func = super(FunctionNode, self).eval(vars)
            return func(*[a.eval(vars) for a in self.args])

    def unary_op(tok):
        op, rhs = tok[0]
        if isinstance(rhs, LiteralNode):
            rhs.value = -rhs.value
            return rhs
        else:
            return UnaryOpNode(tok)

    expression = Forward()

    LPAR, RPAR, DOT, LBRAC, RBRAC = map(Suppress, "().{}")

    identifier = Word(alphas + "_", alphanums + "_")

    integer = Word('+' + '-' + nums, nums)
    fractional = Combine(integer + '.' + Word(nums))
    literal = fractional | integer
    literal.setParseAction(LiteralNode)

    arglist = delimitedList(expression)

    seqrange = expression + Suppress('..') + expression
    seqrange.setParseAction(lambda t: range(t[0], t[1] + 1))
    sequence = LBRAC + (seqrange | arglist) + RBRAC
    sequence.setParseAction(lambda t: Sequence(t[0]))

    roll = Optional(integer, default=1) + Suppress("d") + (integer | sequence)
    roll.setParseAction(lambda t: DieRoll(*t))

    function = identifier + LPAR + Optional(arglist) + RPAR
    function.setParseAction(FunctionNode)

    seqexpr = (roll | sequence | function) + DOT + function

    variable = identifier.copy()
    variable.setParseAction(VariableNode)

    atom = roll | literal | sequence | seqexpr | function | variable

    expoop = Literal('^')
    signop = oneOf("+ -")
    multop = oneOf("* /")
    plusop = oneOf("+ -")

    # noinspection PyUnresolvedReferences
    expression << operatorPrecedence(
        atom,
        [
            (expoop, 2, opAssoc.LEFT, BinaryOpNode),
            (signop, 1, opAssoc.RIGHT, unary_op),
            (multop, 2, opAssoc.LEFT, BinaryOpNode),
            (plusop, 2, opAssoc.LEFT, BinaryOpNode),
        ]
    )

    return expression

grammar = _grammar()


class Roll(object):
    default_vars = {
        'trunc': math.trunc,
        'floor': math.floor,
        'ceil': math.ceil,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'abs': abs,
        'log': math.log,
        'sqrt': math.sqrt,
        'pow': math.pow,
    }

    def __init__(self, expr, parser=None):
        parser = parser or grammar
        self.raw = expr
        self.parsed = parser.parseString(expr, True)[0]
        self.vars = {}

    def eval(self, **vars):
        _vars = dict(self.default_vars)
        _vars.update(vars)
        return self.parsed.eval(_vars)

    def __repr__(self):
        return "Roll(%r)" % self.raw


def roll(expr, **vars):
    roll = Roll(expr)
    return roll.eval(**vars)
