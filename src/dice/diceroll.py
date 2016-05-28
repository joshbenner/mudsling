"""
Generic dice-rolling library based on pyparsing.

Example usage:
>>> roll = RollResult('1d20 + 2 + STR', desc=True, STR=2)
>>> print roll.desc + ' = ' + str(roll.result)

Tips:
* RollResult class is great for doing everything all at once.
* Roll class is useful for storing a roll that will occur multiple times.

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
       rollmod ::= ("d" | "k" | "r" | "e" | "x") [integer]
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
    x[N=<max>] -- Modified explode that rolls only one die during explosion.

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
    min(n, n1, ..., nN)
    max(n, n1, ..., nN)
    sum(n, n1, ..., nN))
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

TODO:
* Implement vs checks (as separate class?)
"""
import math
import random
import operator
import pyparsing
from collections import OrderedDict

pyparsing.ParserElement.enablePackrat()


## {{{ http://code.activestate.com/recipes/578433/ (r1)
class SlotPickleMixin(object):
    def __all_slots(self):
        slots = []
        for cls in self.__class__.__mro__:
            if '__slots__' in cls.__dict__:
                slots.extend(list(cls.__slots__))
        return slots

    def __getstate__(self):
        return dict(
            (slot, getattr(self, slot))
            for slot in self.__all_slots()
            if hasattr(self, slot)
        )

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)
## end of http://code.activestate.com/recipes/578433/ }}}


def _grammar():
    from pyparsing import alphas, alphanums, nums
    from pyparsing import oneOf, Suppress, Optional, Group, ZeroOrMore, NotAny
    from pyparsing import Forward, operatorPrecedence, opAssoc, Word, White
    from pyparsing import delimitedList, Combine, Literal, OneOrMore

    expression = Forward()

    LPAR, RPAR, DOT, LBRAC, RBRAC = map(Suppress, "().{}")
    nw = NotAny(White())

    identifier = Word(alphas + "_", alphanums + "_")

    integer = Word(nums)
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

    rollmod = nw + Group(oneOf("d k r e x") + Optional(integer))
    numdice = Optional(integer, default=1)
    roll = numdice + nw + Suppress("d") + nw + (integer | sequence)
    roll += Group(ZeroOrMore(rollmod))
    roll.setParseAction(DieRollNode)

    call = LPAR + Group(Optional(arglist)) + RPAR
    function = identifier + call
    function.setParseAction(FunctionNode)

    seqexpr = ((roll | sequence | function)
               + Group(OneOrMore(DOT + identifier + call)))
    seqexpr.setParseAction(SeqMethodNode)

    variable = Word(alphas + "_", alphanums + "_ ")
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
        if keep < 0:  # Keep last N.
            s = s[keep:]
        else:         # Keep first N.
            s = s[:keep]
    if drop is not None:
        if drop < 0:  # Drop last N.
            s = s[:-drop]
        else:         # Drop first N.
            s = s[drop:]
    d.clear()
    d.update(s)


class DynamicVariable(SlotPickleMixin):
    """
    A variable value which knows how to evaluate itself in an expression. Akin
    to properties, which act like attributes, but actually execute to yield a
    value.
    """
    __slots__ = ()

    def eval(self, vars, state):
        """
        Evaluate the dynamic variable.

        @return: A tuple containing the resulting value and the description if
            desc=True in the evaluation state.
        @rtype: C{tuple}
        """
        raise NotImplementedError("'%s' has not implemented eval()"
                                  % self.__class__.__name__)


class Sequence(list):
    """
    Thin sub-class of list that does almost nothing other than defines a class
    specific to lists of values in dice rolls.
    """
    __slots__ = ()

    def __str__(self):
        return '{%s}' % ', '.join(map(str, self))


class EvalNode(SlotPickleMixin):
    """
    Generic EvalNode. EvalNodes form the tree that is generated as a result of
    parsing a roll expression.
    """
    __slots__ = ()

    def eval(self, vars, state):
        raise NotImplementedError()

    def coerce_numeric(self, vars, state):
        return self.eval(vars, state)


class SequenceNode(EvalNode):
    """
    An EvalNode representing a sequence of values in a roll expression.
    """
    __slots__ = ('data', 'start', 'stop')

    def __init__(self, lst=None, start=None, stop=None):
        self.start = self.stop = None
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
        gen_desc = state.get('desc', False)
        desc = descs = startdesc = stopdesc = ''
        if self.is_range():
            start, startdesc = self.start.coerce_numeric(vars, state)
            stop, stopdesc = self.stop.coerce_numeric(vars, state)
            values = range(start, stop + 1)
        else:
            values = []
            descs = []
            for datum in self.data:
                v, d = datum.coerce_numeric(vars, state)
                values.append(v)
                if gen_desc and isinstance(datum, OpNode):
                    d += ' = %s' % v
                descs.append(d)
        if gen_desc:
            if self.is_range():
                desc = "{%s..%s}" % (startdesc, stopdesc)
            else:
                desc = "{%s}" % ', '.join(descs)
        return Sequence(values), desc

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
    """
    An EvalNode representing a die roll within a roll expression.
    """
    __slots__ = ('num_dice', 'sides', 'mods')
    mod_funcs = {
        'd': lambda self, r, v, s, drop=1: self.drop_lowest(r, s, drop),
        'k': lambda self, r, v, s, keep=1: self.keep_highest(r, s, keep),
        'r': lambda self, r, v, s, low=None: self.reroll_low(r, v, s, low),
        'e': lambda self, r, v, s, high=None: self.explode(r, v, s, high),
        'x': lambda self, r, v, s, high=None: self.modified_explode(r, v, s,
                                                                    high),
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

    def drop_lowest(self, rolls, state, drop=1):
        if state.get('desc', False):
            descs = state['rolldescs'][state['current roll']]
            copy = OrderedDict(rolls)
            sort_dict(copy, key=lambda r: r[1], drop=drop)
            for id, result in rolls.iteritems():
                if id not in copy:
                    rolls[id] = 0
                    descs[id] = "%d[0]" % result
        else:
            sort_dict(rolls, key=lambda r: r[1], drop=drop)

    def keep_highest(self, rolls, state, keep=1):
        if state.get('desc', False):
            descs = state['rolldescs'][state['current roll']]
            copy = OrderedDict(rolls)
            sort_dict(copy, key=lambda r: r[1], keep=-keep)
            for id, result in rolls.iteritems():
                if id not in copy:
                    rolls[id] = 0
                    descs[id] = "%d[0]" % result
        else:
            sort_dict(rolls, key=lambda r: r[1], keep=-keep)

    def reroll_low(self, rolls, vars, state, low=None):
        """
        Re-roll any rolls <= `low`. Expects all members to be integers.
        """
        low = low or self.min_face(vars, state)
        high_faces = self.faces_above(low, vars, state)
        if not high_faces:
            return
        desc = state.get('desc', False)
        for id, result in rolls.iteritems():
            if result <= low:
                rolls[id] = random.choice(high_faces)
                if desc:
                    newdesc = "%d[%d]" % (result, rolls[id])
                    state['rolldescs'][state['current roll']][id] = newdesc

    def explode(self, rolls, vars, state, high=None):
        high = high or self.max_face(vars, state)
        desc = state.get('desc', False)
        for id, result in rolls.iteritems():
            while result >= high:
                result, newid = self.roll_die(vars, state)
                rolls[id] += result
                if desc:
                    olddesc = state['rolldescs'][state['current roll']][id]
                    newdesc = '%s!%s' % (olddesc, result)
                    state['rolldescs'][state['current roll']][id] = newdesc

    def modified_explode(self, rolls, vars, state, high=None):
        high = high or self.num_dice * self.sides
        desc = state.get('desc', False)
        result = sum(rolls.itervalues())
        while result >= high:
            # After first explode, we only explode a single die.
            high = self.sides
            result, id = self.roll_die(vars, state)
            rolls[id] = result
            if desc:
                state['rolldescs'][state['current roll']][id] = str(result)

    def eval(self, vars, state):
        # Sanity-check the mods, convert nodes to values.
        for mod in self.mods:
            if mod[0] == 'e':
                explode_min = (int(mod[1]) if len(mod) > 1
                               else self.max_face(vars, state))
                if explode_min <= self.min_face(vars, state):
                    raise pyparsing.ParseException("All rolls explode!")
        name = str(self)
        key = "%s count" % name
        count = vars.get(key, 0) + 1
        vars[key] = count
        id = "%s#%d" % (name, count)
        state['current roll'] = id
        rolls = self._eval(vars, state)
        if 'rolls' not in state:
            state['rolls'] = {}
        state['rolls'][id] = rolls
        if state.get('desc', False):
            if 'rolldescs' not in state:
                state['rolldescs'] = {}
            state['rolldescs'][id] = OrderedDict((i, str(r))
                                                 for i, r in rolls.iteritems())
        if not state.get('maxroll', False) and not state.get('minroll', False):
            for mod in self.mods:
                args = [a.eval(vars, state)[0] if isinstance(a, EvalNode)
                        else a for a in mod[1:]]
                self.mod_funcs[mod[0]](self, rolls, vars, state, *args)
            result = Sequence(rolls.itervalues())
        else:
            result = sum(rolls)
        if state.get('desc', False):
            if len(state['rolldescs'][id]) > 1:
                rollsdesc = '+'.join(state['rolldescs'][id].values()) + '='
            else:
                rollsdesc = ''
            rollsdesc += str(sum(result))
            # Show runtime sides value.
            sides = (self.sides.eval(vars, state)[1]
                     if isinstance(self.sides, EvalNode) else str(self.sides))
            die = "%sd%s%s" % (self.num_dice, sides, self.mod_desc())
            desc = "%s[%s]" % (die, rollsdesc)
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

    def roll_die(self, vars, state):
        result = random.choice(self.all_sides(vars, state))
        type = self.die_type()
        key = "%s count" % type
        if key not in state:
            state[key] = 1
        else:
            state[key] += 1
        return result, "%s#%d" % (type, state[key])

    def coerce_numeric(self, vars, state):
        result, desc = self.eval(vars, state)
        return sum(result) if isinstance(result, Sequence) else result, desc


class LiteralNode(EvalNode):
    """
    A generic literal EvalNode that stores a literal numeric value as found in
    the roll expression.
    """
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

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
        super(IntegerNode, self).__init__(int(tok[0]))


class FloatNode(LiteralNode):
    def __init__(self, tok):
        super(FloatNode, self).__init__(float(tok[0]))


class VariableNode(EvalNode):
    """
    A variable EvalNode. Simply accesses the value passed in by the caller.
    """
    __slots__ = ('name', 'original')

    def __init__(self, tok):
        self.original = tok[0].strip()
        self.name = self.original.lower()

    def eval(self, vars, state):
        need_desc = state.get('desc', False)
        if self.name in vars:
            expr = vars[self.name]
            desc = None
        elif '__var' in vars:
            expr, desc = vars['__var'](self.original, vars, state)
        else:
            raise NameError("Variable '%s' not found" % self.name)

        if isinstance(expr, EvalNode):
            value, desc = expr.eval(vars, state)
        elif isinstance(expr, Roll):
            value, desc = expr._eval(vars, state)
            if need_desc and isinstance(expr.parsed, BinaryOpNode):
                desc += ' = %s' % value
        elif isinstance(expr, RollResult):
            value = expr.result
            desc = str(value)
        elif isinstance(expr, DynamicVariable):
            value, desc = expr.eval(vars, state)
        else:
            value = expr

        if need_desc:
            if not desc:
                desc = "%s[%s]" % (self.original, value)
        else:
            desc = ''
        return value, desc

    def __repr__(self):
        return "Variable(%s)" % self.name

    def __str__(self):
        return self.name


class OpNode(EvalNode):
    """
    Generic operator EvalNode. Establishes a storage framework for operator
    nodes and also handles adding parens when needed in a string representation
    of the operation.
    """
    __slots__ = ('op', 'opfunc', 'assoc')
    ops = {}

    def __init__(self, op):
        self.op = op
        self.opfunc, self.assoc = self.ops[op]

    def add_parens(self, expr):
        """
        Add parens when the passed expression is of lower associativity than
        this operator.
        """
        return isinstance(expr, OpNode) and expr.assoc < self.assoc


class BinaryOpNode(OpNode):
    """
    An EvalNode for an operations that takes two operands.
    """
    __slots__ = ('lhs', 'rhs')
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
    """
    An EvalNode for an operator that takes only a single operand.
    """
    __slots__ = ('rhs',)
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
    """
    An EvalNode for calling a function. Functions are Python functions passed
    into the evaluation as variables.
    """
    __slots__ = ('args',)

    def __init__(self, tok):
        super(FunctionNode, self).__init__(tok)
        self.args = tok[1]

    def __repr__(self):
        return "Func:%s(%s)" % (self.name, ', '.join(map(repr, self.args)))

    def __str__(self):
        return "%s(%s)" % (self.name, ', '.join(map(str, self.args)))

    def eval(self, vars, state):
        func = super(FunctionNode, self).eval(vars, state)[0]
        args, adescs = self._prep_args(self.args, vars, state)
        result = func(*args)
        if state.get('desc', False):
            desc = "%s(%s)=>%s" % (self.name, ', '.join(adescs), result)
        else:
            desc = ''
        return result, desc

    def _prep_args(self, args, vars, state):
        newargs = []
        descs = []
        seqfunc = self.name.startswith('seq.')
        for a in args:
            if not seqfunc and (isinstance(a, SequenceNode)
                                or isinstance(a, DieRollNode)):
                value, desc = a.coerce_numeric(vars, state)
                if desc:
                    desc += "=>%s" % value
            else:
                value, desc = a.eval(vars, state)
            newargs.append(value)
            descs.append(desc)
        return newargs, descs


class SeqMethodNode(FunctionNode):
    """
    An EvalNode for sequence methods. These are much like functions with some
    slightly different handling of arguments and description.
    """
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
        args, adescs = self._prep_args(self.args, vars, state)
        func = VariableNode.eval(self, vars, state)[0]
        result = func(*args)
        if state.get('desc', False):
            fname = self.name[4:]
            argdescs = ', '.join(adescs[1:])
            desc = '%s.%s(%s)=>%s' % (adescs[0], fname, argdescs, result)
        else:
            desc = ''
        return result, desc

grammar = _grammar()


class RollResult(SlotPickleMixin):
    """
    A RollResult represents a specific cast of a Roll.
    """
    __slots__ = ('roll', 'state', 'desc', 'result')

    def __init__(self, roll, **vars):
        if isinstance(roll, basestring):
            roll = Roll(roll)
        self.roll = roll
        self.state = {'desc': True}
        result, self.desc = roll._eval(vars, self.state)
        self.result = sum(result) if isinstance(result, list) else result

    def __repr__(self):
        return "RollResult(%r)" % str(self.roll)

    def __str__(self):
        return "%s = %s" % (self.desc or self.roll, self.result)


class Roll(SlotPickleMixin):
    """
    A Roll is the representation of a roll formula. To perform the roll it
    represents, call .eval().

    Roll class provides a series of default variables/functions for use in
    roll expressions.
    """
    default_vars = {
        'trunc': math.trunc,
        'floor': math.floor,
        'ceil': math.ceil,
        'round': round,
        'min': lambda *a: min(a),
        'max': lambda *a: max(a),
        'sum': lambda *a: sum(a),
        'abs': abs,
        'log': math.log,
        'sqrt': math.sqrt,
        'pow': math.pow,
        'seq.sum': sum,
        'seq.max': lambda s: max(s),  # Use lambda to avoid multi-args.
        'seq.min': lambda s: min(s),
        'seq.highest': lambda s, n=1: Sequence(sorted(s)[-n:]),
        'seq.lowest': lambda s, n=1: Sequence(sorted(s)[:n]),
        'seq.drop': lambda s, *v: Sequence(r for r in s if r not in v),
        'seq.average': lambda s: sum(s) / float(len(s))
    }
    __slots__ = ('raw', 'parsed', 'vars')

    def __init__(self, expr, parser=None, vars=None):
        self._parse(expr, parser)
        self.vars = vars or {}

    def _parse(self, expr, parser=None):
        parser = parser or grammar
        if isinstance(expr, basestring):
            self.raw = expr
            self.parsed = parser.parseString(expr, True)[0]
        elif isinstance(expr, EvalNode):
            self.raw = str(expr)
            self.parsed = expr
        else:
            raise TypeError("Roll takes string or EvalNode.")

    def __eq__(self, other):
        if isinstance(other, Roll):
            return repr(self.parsed) == repr(other.parsed)
        return False

    def eval(self, state=None, desc=False, **vars):
        state = state if state is not None else {}
        state['desc'] = desc
        result, d = self._eval(vars, state)
        if isinstance(result, list):
            result = sum(result)
        return (result, d) if desc else result

    def _eval(self, vars, state):
        _vars = dict(self.default_vars)
        _vars.update(self.vars)
        _vars.update(vars)
        return self.parsed.eval(_vars, state)

    def limits(self, vars=None, state=None):
        vars = vars or {}
        original_state = state or {}
        state = dict(original_state)
        state['minroll'] = True
        minroll = self._eval(vars, state)[0]
        state = dict(original_state)
        state['maxroll'] = True
        maxroll = self._eval(vars, state)[0]
        return minroll, maxroll

    @property
    def min(self):
        return self.limits()[0]

    @property
    def max(self):
        return self.limits()[1]

    def update(self, expr, parser=None, vars=None):
        self._parse(expr, parser)
        self.vars.update(vars)

    def __repr__(self):
        return "Roll(%r)" % self.raw

    def __str__(self):
        return str(self.parsed)

    def __getstate__(self):
        state = super(Roll, self).__getstate__()
        if 'parsed' in state:
            del state['parsed']
        return state

    def __setstate__(self, state):
        super(Roll, self).__setstate__(state)
        self._parse(self.raw)


def roll(expr, **vars):
    """
    Convenience function for executing a quick roll and returning the result.

    If you need more, use L{Roll} or L{RollResult}.
    """
    roll = Roll(expr)
    return roll.eval(**vars)
