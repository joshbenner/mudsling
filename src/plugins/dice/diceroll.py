"""
Generic dice-rolling library based on pyparsing.

Extended BNF (same as Python specification):
     lowercase ::= "a"..."z"
     uppercase ::= "A"..."Z"
        letter ::= lowercase | uppercase
         digit ::= "0"..."9"
  alphanumeric ::= letter | digit
    identifier ::= (letter | "_") alphanumeric+
       integer ::= ["+" | "-"] digit+
    fractional ::= integer "." digit+
        number ::= integer | fractional
        seqnum ::= ["-"] (number | identifier)
      sequence ::= "{" seqnum ( ("," seqnum)* | (".." seqnum) ) "}"
       rollmod ::= ("d" | "k" | "r" | "e" | "o") integer
          roll ::= [integer] "d" (integer | sequence) [rollmod]
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
          atom ::= seqexpr | roll | literal | sequence | function | identifier
     operation ::= unary | exponent | multiply | divide | add | subtract
    expression ::= group | atom | operation

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
    .drop(value1[, value2...]) => Sequence lacking any specified value.
    .dropLowest(N) => Sequence without its N lowest elements.
    .dropHighest(N) => Sequence without its N highest elements.

Functions:
    trunc
    floor
    ceil
    round
    min
    max
    sum
    pow
    abs

Notes:
* Adding a sequence to a number coerces the sequence to a sum of its elements.
"""
import math
import random
import operator
import pyparsing

pyparsing.ParserElement.enablePackrat()


def _grammar():
    from pyparsing import alphas, alphanums, nums
    from pyparsing import oneOf, Suppress, Optional, Group
    from pyparsing import Forward, operatorPrecedence, opAssoc, Word
    from pyparsing import delimitedList, Combine, Literal

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
    sequence.setParseAction(lambda t: Sequence(t))

    roll = Optional(integer, default=1) + Suppress("d") + (integer | sequence)
    roll.setParseAction(lambda t: DieRoll(*t))

    call = LPAR + Group(Optional(arglist)) + RPAR
    function = identifier + call
    function.setParseAction(FunctionNode)

    seqexpr = (roll | sequence | function) + DOT + identifier + call
    seqexpr.setParseAction(SeqMethodNode)

    variable = identifier.copy()
    variable.setParseAction(VariableNode)

    atom = seqexpr | roll | literal | sequence | function | variable

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


class EvalNode(object):
    def eval(self, vars=None, flags=None):
        raise NotImplementedError()

    def coerce_numeric(self, vars=None, flags=None):
        return self.eval(vars, flags)


class Sequence(EvalNode):
    data = []

    def __init__(self, lst=None):
        self.data = list(lst) if lst else []

    def __iter__(self):
        return (d for d in self.data)

    def __len__(self):
        return len(self.data)

    def sum(self, vars=None, flags=None):
        return sum([n.coerce_numeric(vars, flags) for n in self.data])

    def coerce_numeric(self, vars=None, flags=None):
        return self.sum(vars, flags)

    def _op(self, op, other, *args):
        if isinstance(other, Sequence):
            other = other.sum()
        if isinstance(other, int) or isinstance(other, float):
            return getattr(self.sum(), op)(other, *args)

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

    __neg__ = lambda self: -self.sum()
    __pos__ = lambda self: self.sum()
    __abs__ = lambda self: abs(self.sum())
    __invert__ = lambda self: ~self.sum()
    __index__ = lambda self: int(self.sum())

    def __repr__(self):
        return "Sequence(%r)" % self.data

    def eval(self, vars=None, flags=None):
        if flags is not None:
            if flags.get('minroll', False) or flags.get('maxroll', False):
                return self.coerce_numeric(vars, flags)
        return self


class DieRoll(EvalNode):
    def __init__(self, num_dice, sides):
        super(DieRoll, self).__init__()
        if isinstance(sides, basestring):
            sides = int(sides)
        self.num_dice = int(num_dice)
        self.sides = sides

    def __repr__(self):
        return "DieRoll(%r, %r)" % (self.num_dice, self.sides)

    def eval(self, vars=None, flags=None):
        if flags is not None:
            if flags.get('maxroll', False):
                if isinstance(self.sides, list):
                    return Sequence([max(self.sides)] * self.num_dice)
                else:
                    return Sequence([self.sides] * self.num_dice)
            elif flags.get('minroll', False):
                if isinstance(self.sides, list):
                    return Sequence([min(self.sides)] * self.num_dice)
                else:
                    return Sequence([1] * self.num_dice)
        else:
            if isinstance(self.sides, list):
                return Sequence(random.choice(self.sides)
                                for _ in range(1, self.num_dice + 1))
            else:
                return Sequence(random.randint(1, self.sides + 1)
                                for _ in range(1, self.num_dice + 1))

    def coerce_numeric(self, vars=None, flags=None):
        sequence = self.eval(vars, flags)
        return sequence.sum(vars, flags)


class LiteralNode(EvalNode):
    def __init__(self, tok):
        try:
            self.value = int(tok[0])
        except ValueError:
            self.value = float(tok[0])

    def eval(self, vars=None, flags=None):
        return self.value

    def __repr__(self):
        return "Literal(%s)" % str(self.value)

    def _op(self, op, other, *args):
        other = other.value if isinstance(other, LiteralNode) else other
        return getattr(self.value, op)(other, *args)

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

    __neg__ = lambda self: -self.value
    __pos__ = lambda self: self.value
    __abs__ = lambda self: abs(self.value)
    __invert__ = lambda self: ~self.value
    __index__ = lambda self: int(self.value)


class VariableNode(EvalNode):
    def __init__(self, tok):
        self.name = tok[0]

    def eval(self, vars=None, flags=None):
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
        self.lhs, self.op, self.rhs = tok[0][:3]
        # Sequential binary operations in the same family are sent all at once,
        # so we iterate over them and push the left side deeper as we go.
        for op, rhs in zip(tok[0][3::2], tok[0][4::2]):
            self.lhs = BinaryOpNode([[self.lhs, self.op, self.rhs]])
            self.op = op
            self.rhs = rhs

    def __repr__(self):
        return "(%s %s %s)" % (self.lhs, self.op, self.rhs)

    def eval(self, vars=None, flags=None):
        lhs = self.lhs.coerce_numeric(vars, flags)
        rhs = self.rhs.coerce_numeric(vars, flags)
        return self.ops[self.op](lhs, rhs)


class UnaryOpNode(EvalNode):
    ops = {
        '-': operator.neg,
        '+': lambda x: x,
    }

    def __init__(self, tok):
        self.op, self.rhs = tok[0]

    def __repr__(self):
        return "%s%s" % (self.op, self.rhs)

    def eval(self, vars=None, flags=None):
        return self.ops[self.op](self.rhs.coerce_numeric(vars, flags))


class FunctionNode(VariableNode):
    def __init__(self, tok):
        super(FunctionNode, self).__init__(tok)
        self.args = tok[1]

    def __repr__(self):
        return "%s(%s)" % (self.name, ', '.join(map(repr, self.args)))

    def eval(self, vars=None, flags=None):
        func = super(FunctionNode, self).eval(vars, flags)
        return func(*[a.eval(vars, flags) for a in self.args])


class SeqMethodNode(FunctionNode):
    def __init__(self, tok):
        sequence, name, args = tok
        name = 'seq.' + name
        args.insert(0, sequence)
        super(SeqMethodNode, self).__init__([name, args])

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
        'seq.sum': sum,
        'seq.max': max,
        'seq.min': min,
        'seq.highest': lambda s, n: Sequence(sorted(s, reverse=True)[:n]),
        'seq.lowest': lambda s, n: Sequence(sorted(s)[:n]),
        'seq.drop': lambda s, *v: Sequence(r for r in s if r not in v),
        'seq.dropLowest': lambda s, n: Sequence(sorted(s)[n:]),
        'seq.dropHighest': lambda s, n: Sequence(sorted(s, reverse=True)[n:]),
        'seq.average': lambda s: sum(s) / float(len(s))
    }

    def __init__(self, expr, parser=None):
        parser = parser or grammar
        self.raw = expr
        self.parsed = parser.parseString(expr, True)[0]
        self.vars = {}

    def __eq__(self, other):
        if isinstance(other, Roll):
            return repr(self.parsed) == repr(other.parsed)
        return False

    def eval(self, **vars):
        return self._eval(vars, {})

    def _eval(self, vars, flags):
        _vars = dict(self.default_vars)
        _vars.update(vars)
        return self.parsed.eval(_vars, flags)

    def limits(self, **vars):
        minroll = self._eval(vars, {'minroll': True})
        maxroll = self._eval(vars, {'maxroll': True})
        return minroll, maxroll

    def __repr__(self):
        return "Roll(%r)" % self.raw


def roll(expr, **vars):
    roll = Roll(expr)
    return roll.eval(**vars)
