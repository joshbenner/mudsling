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
       rollmod ::= ("d" | "k" | "r" | "e") [integer]
          roll ::= [integer] "d" (integer | sequence) (rollmod)*
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

Dice Roll Modifiers:
    d[N=1] -- Drop lowest N rolls.
    k[N=1] -- Keep highest N rolls.
    r[N=1] -- Re-roll values <= N.
    e[N=<max>] -- Explode (re-roll) values >= N (default highest), keep all.

Sequence Methods:
    .max() => Largest value in the sequence.
    .min() => Smallest value in the sequence.
    .sum() => Result of adding all sequence elements together.
    .highest(N) => Sequence containing greatest N elements.
    .lowest(N) => Sequence containing lowest N elements.
    .drop(value1[, value2...]) => Sequence lacking any specified value.

Functions:
    trunc(f)
    floor(f)
    ceil(f)
    round(f[, digits])
    min(s) or min(n, n1, ..., nN)
    max(s) or max(n, n1, ..., nN)
    sum(s[, start])
    pow(n, e)
    abs(n)

Examples:
    2d10 -- Yields a sequence containing two rolls of a 10-sided die.
    2d20e -- Yields a sequence containing two rolls of 20-sided die as well as
        any additional rolls resulting from natural 20s.
    1d20 + 5 -- Yields result of rolling a d20 and adding 5.
    d{2, 4, 6} -- Yields 2, 4, or 6 with equal probability.
    2d20.minSum(2) -- Yields the sequence whose sum is least of two 2d20 rolls.
    {STR, DEX}.max() -- Yields the greater of STR or DEX identifiers.
    ceil(d6 / 2) -- Yields the result of rolling a d6 rounded up.

Notes:
* Adding a sequence to a number coerces the sequence to a sum of its elements.
"""
#TODO: Produce a log of natural rolls and modifiers available on Roll instance.
import math
import random
import operator
import pyparsing
import uuid
from collections import OrderedDict

pyparsing.ParserElement.enablePackrat()


def _grammar():
    from pyparsing import alphas, alphanums, nums
    from pyparsing import oneOf, Suppress, Optional, Group, ZeroOrMore
    from pyparsing import Forward, operatorPrecedence, opAssoc, Word
    from pyparsing import delimitedList, Combine, Literal, OneOrMore

    expression = Forward()

    LPAR, RPAR, DOT, LBRAC, RBRAC = map(Suppress, "().{}")

    identifier = Word(alphas + "_", alphanums + "_")

    integer = Word('+' + '-' + nums, nums)
    integer.setParseAction(IntegerNode)
    fractional = Combine(Word('+' + '-' + nums, nums) + '.' + Word(nums))
    fractional.setParseAction(FloatNode)
    literal = fractional | integer

    arglist = delimitedList(expression)

    seqrange = LBRAC + expression + Suppress('..') + expression + RBRAC
    seqrange.setParseAction(lambda t: SequenceNode(start=t[0], stop=t[1]))
    seqexplicit = LBRAC + Optional(arglist) + RBRAC
    seqexplicit.setParseAction(lambda t: SequenceNode(lst=t))
    sequence = seqrange | seqexplicit

    rollmod = Group(oneOf("d k r e") + Optional(integer))
    roll = Optional(integer, default=1) + Suppress("d") + (integer | sequence)
    roll += Group(ZeroOrMore(rollmod))
    roll.setParseAction(DieRollNode)

    call = LPAR + Group(Optional(arglist)) + RPAR
    function = identifier + call
    function.setParseAction(FunctionNode)

    seqexpr = ((roll | sequence | function)
               + Group(OneOrMore(DOT + identifier + call)))
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
            (signop, 1, opAssoc.RIGHT, UnaryOpNode),
            (multop, 2, opAssoc.LEFT, BinaryOpNode),
            (plusop, 2, opAssoc.LEFT, BinaryOpNode),
        ]
    )

    return expression


def sort_dict(d, cmp=None, key=None, reverse=False, keep=None, drop=None):
    s = sorted(d.items(), cmp=cmp, key=key, reverse=reverse)
    if keep is not None:
        if keep < 0:
            s = s[keep:]
        else:
            s = s[:keep]
    if drop is not None:
        if drop < 0:
            s = s[:drop]
        else:
            s = s[drop:]
    d.clear()
    d.update(s)


def drop_lowest(sequence, n=1):
    return Sequence(sorted(sequence)[n:])


def keep_highest(sequence, n=1):
    return Sequence(sorted(sequence, reverse=True)[:n])


class Sequence(list):
    def __str__(self):
        return '{%s}' % ', '.join(map(str, self))


class EvalNode(object):
    def eval(self, vars, state):
        raise NotImplementedError()

    def coerce_numeric(self, vars, state):
        return self.eval(vars, state)


class SequenceNode(EvalNode):
    data = []
    start = None
    stop = None

    def __init__(self, lst=None, start=None, stop=None):
        if lst is not None:
            self.data = list(lst) if lst else []
        elif start is not None and stop is not None:
            # Could be nodes requiring eval-time values.
            self.start = start
            self.stop = stop
        else:
            self.data = []

    def is_range(self):
        return self.start is not None and self.stop is not None

    def eval(self, vars, state):
        if self.is_range():
            start, startdesc = self.start.coerce_numeric(vars, state)
            stop, stopdesc = self.stop.coerce_numeric(vars, state)
            seq = Sequence(range(start, stop + 1))
        else:
            seq = Sequence(self.data)
            startdesc = stopdesc = ''
        if state.get('desc', False):
            if self.is_range():
                desc = "{%s..%s}" % (startdesc, stopdesc)
            else:
                desc = "{%s}" % ', '.join(map(str, seq))
        else:
            desc = ''
        return seq, desc

    def coerce_numeric(self, vars, state):
        result, desc = self.eval(vars, state)
        return sum(result), desc

    def __repr__(self):
        if self.is_range():
            return "SequenceNode(start=%r, stop=%r)" % (self.start,
                                                        self.stop)
        else:
            return "SequenceNode(%r)" % self.data

    def __str__(self):
        if self.is_range():
            return '{%s..%s}' % (self.start, self.stop)
        else:
            return '{%s}' % ', '.join(map(str, self.data))


class DieRollNode(EvalNode):
    mod_funcs = {
        'd': lambda s, r, v, f, drop=1: drop_lowest(r, drop),
        'k': lambda s, r, v, f, keep=1: keep_highest(r, keep),
        'r': lambda s, r, v, f, low=None: s.reroll_low(r, v, f, low),
        'e': lambda s, r, v, f, high=None: s.explode(r, v, f, high),
    }

    def __init__(self, tok):
        #: @type num_dice: IntegerNode
        #: @type sides: IntegerNode or SequenceNode
        #: @type mods: ParseResult
        num_dice, sides, mods = tok
        self.num_dice = int(num_dice)
        self.sides = sides
        self.mods = map(tuple, mods)

    def __repr__(self):
        return "DieRollNode(%r, %r, %r)" % (self.num_dice, self.sides,
                                            self.mods)

    def __str__(self):
        return "%sd%s%s" % (self.num_dice, self.sides, self.mod_desc())

    def mod_desc(self):
        s = ''
        for mod in self.mods:
            s += mod[0]
            if len(mod) > 1:
                s += str(mod[1])
        return s

    def die_type(self):
        return "d%s" % self.sides

    def roll_die(self, vars, state):
        result = random.choice(self.all_sides(vars, state))
        type = self.die_type()
        key = "%s count" % type
        if key not in state:
            state[key] = 1
        else:
            state[key] += 1
        return result, "%s#%d" % (type, state[key])

    def all_sides(self, vars, state):
        # Check the cache.
        name = "all sides of %s%s" % (self.num_dice, self.die_type())
        if name in vars:
            return vars[name]
        sides = self.sides.eval(vars, state)[0]
        if isinstance(sides, int):
            sides = range(1, sides + 1)
        vars[name] = sides
        return sides

    def min_face(self, vars, state):
        return min(self.all_sides(vars, state))

    def max_face(self, vars, state):
        return max(self.all_sides(vars, state))

    def faces_below(self, face, vars, state):
        return [f for f in self.all_sides(vars, state) if f < face]

    def faces_above(self, face, vars, state):
        return [f for f in self.all_sides(vars, state) if f > face]

    def drop_lowest(self, rolls, vars, state, drop=1):
        return sort_dict(rolls, key=lambda r: r[1], keep=-drop)

    def reroll_low(self, rolls, vars, state, low=None):
        """
        Re-roll any rolls <= `low`. Expects all members to be integers.
        """
        low = low or self.min_face(vars, state)
        high_faces = self.faces_above(low, vars, state)
        if not high_faces:
            return
        for id, result in rolls.iteritems():
            if result <= low:
                rolls[id] = random.choice(high_faces)

    def explode(self, rolls, vars, state, high=None):
        high = high or self.max_face(vars, state)
        for id, result in rolls.iteritems():
            while result >= high:
                result = self.roll_die(vars, state)
                rolls[uuid.uuid1()] = result

    def eval(self, vars, state):
        # Sanity-check the mods, convert nodes to values.
        for mod in self.mods:
            if mod[0] == 'e':
                explode_min = (int(mod[1]) if len(mod) > 1
                               else self.max_face(vars, state))
                if explode_min <= self.min_face(vars, state):
                    raise pyparsing.ParseException("All rolls explode!")
        rolls = self._eval(vars, state)
        name = str(self)
        key = "%s count" % name
        count = vars.get(key, 0) + 1
        vars[key] = count
        state["%s#%d" % (name, count)] = rolls
        if not state.get('maxroll', False) and not state.get('minroll', False):
            for mod in self.mods:
                args = [a.eval(vars, state) if isinstance(a, EvalNode) else a
                        for a in mod[1:]]
                self.mod_funcs[mod[0]](self, rolls, vars, state, *args)
            result = Sequence(rolls.itervalues())
        else:
            result = Sequence(rolls)
        if state.get('desc', False):
            rollsdesc = ','.join(map(str, result))
            # Show runtime sides value.
            sides = (self.sides.eval(vars, state)[1]
                     if isinstance(self.sides, EvalNode) else str(self.sides))
            die = "%sd%s%s" % (self.num_dice, sides, self.mod_desc())
            desc = "%s(%s)" % (die, rollsdesc)
        else:
            desc = ''
        return result, desc

    def _eval(self, vars, state):
        if state is not None:
            if state.get('maxroll', False):
                return [self.max_face(vars, state)] * self.num_dice
            elif state.get('minroll', False):
                return [self.min_face(vars, state)] * self.num_dice
        rolls = OrderedDict()
        for _ in range(0, self.num_dice):
            roll, id = self.roll_die(vars, state)
            rolls[id] = roll
        return rolls

    def coerce_numeric(self, vars, state):
        result, desc = self.eval(vars, state)
        return sum(result), desc


class LiteralNode(EvalNode):
    value = None

    def eval(self, vars, state):
        return self.value, str(self.value) if state.get('desc', False) else ''

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__.replace('Node', ''),
                           self.value)

    def __str__(self):
        return str(self.value)

    def _op(self, op, other, *args):
        other = other.value if isinstance(other, LiteralNode) else other
        return getattr(self.value, op)(other, *args)

    __add__ = lambda self, x: self._op('__add__', x)
    __sub__ = lambda self, x: self._op('__sub__', x)
    __mul__ = lambda self, x: self._op('__mul__', x)
    __div__ = lambda self, x: self._op('__div__', x)
    __pow__ = lambda self, x, z=None: self._op('__pow__', x, z)
    __cmp__ = lambda self, x: self._op('__cmp__', x)

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
    __int__ = lambda self: int(self.value)
    __long__ = lambda self: long(self.value)
    __float__ = lambda self: float(self.value)
    __complex__ = lambda self: complex(self.value)


class IntegerNode(LiteralNode):
    def __init__(self, tok):
        self.value = int(tok[0])


class FloatNode(LiteralNode):
    def __init__(self, tok):
        self.value = float(tok[0])


class VariableNode(EvalNode):
    def __init__(self, tok):
        self.name = tok[0]

    def eval(self, vars, state):
        if vars is not None and self.name in vars:
            if state.get('desc', False):
                desc = "%s(%s)" % (self.name, vars[self.name])
            else:
                desc = ''
            return vars[self.name], desc
        raise NameError("Variable '%s' not found" % self.name)

    def __repr__(self):
        return "Variable(%s)" % self.name

    def __str__(self):
        return self.name


class OpNode(EvalNode):
    op = ''
    ops = {}

    def __init__(self, op):
        self.op = op
        self.opfunc, self.assoc = self.ops[op]

    def add_parens(self, expr):
        return isinstance(expr, OpNode) and expr.assoc < self.assoc


class BinaryOpNode(OpNode):
    ops = {
        '^': (operator.pow, 4),
        '*': (operator.mul, 2),
        '/': (operator.div, 2),
        '+': (operator.add, 1),
        '-': (operator.sub, 1),
    }

    def __init__(self, tok):
        self.lhs, op, self.rhs = tok[0][:3]
        super(BinaryOpNode, self).__init__(op)
        # Sequential binary operations in the same family are sent all at once,
        # so we iterate over them and push the left side deeper as we go.
        for op, rhs in zip(tok[0][3::2], tok[0][4::2]):
            self.lhs = BinaryOpNode([[self.lhs, self.op, self.rhs]])
            self.rhs = rhs

    def __repr__(self):
        return "BinaryOp(%r %s %r)" % (self.lhs, self.op, self.rhs)

    def __str__(self):
        return "%s %s %s" % (self.lhs, self.op, self.rhs)

    def eval(self, vars, state):
        lhs, l = self.lhs.coerce_numeric(vars, state)
        rhs, r = self.rhs.coerce_numeric(vars, state)
        if state.get('desc', False):
            l = '(%s)' % l if self.add_parens(self.lhs) else l
            r = '(%s)' % r if self.add_parens(self.rhs) else r
            desc = "%s %s %s" % (l, self.op, r)
        else:
            desc = ''
        return self.opfunc(lhs, rhs), desc


class UnaryOpNode(OpNode):
    ops = {
        '-': (operator.neg, 3),
        '+': (operator.pos, 3),
    }

    def __init__(self, tok):
        op, self.rhs = tok[0]
        super(UnaryOpNode, self).__init__(op)

    def __repr__(self):
        return "UnaryOp(%s%s)" % (self.op, self.rhs)

    def __str__(self):
        return "%s%s" % (self.op, self.rhs)

    def eval(self, vars, state):
        rhs, rd = self.rhs.coerce_numeric(vars, state)
        if state.get('desc', False):
            desc = "%s%s" % (self.op, rd)
        else:
            desc = ''
        return self.opfunc(rhs), desc


class FunctionNode(VariableNode):
    def __init__(self, tok):
        super(FunctionNode, self).__init__(tok)
        self.args = tok[1]

    def __repr__(self):
        return "Func:%s(%s)" % (self.name, ', '.join(map(repr, self.args)))

    def __str__(self):
        return "%s(%s)" % (self.name, ', '.join(map(str, self.args)))

    def eval(self, vars, state):
        func = super(FunctionNode, self).eval(vars, state)[0]
        args = []
        adescs = []
        for a in self.args:
            aval, adesc = a.eval(vars, state)
            args.append(aval)
            adescs.append(adesc)
        result = func(*args)
        if state.get('desc', False):
            desc = "%s(%s)=>%s" % (self.name, ', '.join(adescs), result)
        else:
            desc = ''
        return result, desc


class SeqMethodNode(FunctionNode):
    def __init__(self, tok):
        seqnode, funcs = tok
        last = len(funcs) - 2
        for i in xrange(0, len(funcs), 2):
            name, args = funcs[i:i + 2]
            if i < last:
                seqnode = SeqMethodNode([seqnode, [name, args]])
        name, args = funcs[-2:]
        name = 'seq.' + name
        args.insert(0, seqnode)
        super(SeqMethodNode, self).__init__([name, args])

    def __str__(self):
        args = ', '.join(map(str, self.args[1:]))
        name = self.name[4:]
        return "%s.%s(%s)" % (self.args[0], name, args)

    def eval(self, vars, state):
        result = super(SeqMethodNode, self).eval(vars, state)[0]
        if state.get('desc', False):
            fname = self.name[4:]
            seq = self.args[0].eval(vars, state)[1]
            args = ', '.join(map(str, self.args[1:]))
            desc = '%s.%s(%s)=>%s' % (seq, fname, args, result)
        else:
            desc = ''
        return result, desc

grammar = _grammar()


class RollResult(object):
    def __init__(self, roll, desc=False, **vars):
        if isinstance(roll, basestring):
            roll = Roll(roll)
        self.roll = roll
        self.state = {'desc': desc}
        result, self.desc = roll._eval(vars, self.state)
        self.result = sum(result) if isinstance(result, list) else result

    def __repr__(self):
        return "RollResult(%r)" % str(self.roll)

    def __str__(self):
        return "%s = %s" % (self.desc or self.roll, self.result)


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
        'seq.highest': lambda s, n=1: keep_highest(s, n),
        'seq.lowest': lambda s, n=1: Sequence(sorted(s)[:n]),
        'seq.drop': lambda s, *v: Sequence(r for r in s if r not in v),
        'seq.average': lambda s: sum(s) / float(len(s))
    }

    def __init__(self, expr, parser=None, vars=None):
        parser = parser or grammar
        self.raw = expr
        self.parsed = parser.parseString(expr, True)[0]
        self.vars = vars or {}

    def __eq__(self, other):
        if isinstance(other, Roll):
            return repr(self.parsed) == repr(other.parsed)
        return False

    def eval(self, desc=False, **vars):
        result, d = self._eval(vars, {'desc': desc})
        if isinstance(result, list):
            result = sum(result)
        return (result, d) if desc else result

    def _eval(self, vars, state):
        _vars = dict(self.default_vars)
        _vars.update(self.vars)
        _vars.update(vars)
        return self.parsed.eval(_vars, state)

    def limits(self, **vars):
        minroll = self._eval(vars, {'minroll': True})[0]
        maxroll = self._eval(vars, {'maxroll': True})[0]
        return minroll, maxroll

    def __repr__(self):
        return "Roll(%r)" % self.raw

    def __str__(self):
        return str(self.parsed)


def roll(expr, **vars):
    roll = Roll(expr)
    return roll.eval(**vars)
