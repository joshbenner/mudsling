"""
Utilities that are useful for facilitating the writing of Python code.
"""
import operator


class operator_passthru(object):
    """
    Pass operators through to an attribute of the class.
    """
    operators = []

    def __init__(self, attr, only_same_type=True, operators=None,
                 factory=None):
        self.attr = attr
        self.only_same_type = only_same_type
        self.factory = factory
        if operators is not None:
            self.operators = operators

    def _build_op(self, op, cls):
        attr = self.attr
        same_type = self.only_same_type
        factory = self.factory

        def opfunc(self, *args):
            if same_type and len(args):
                if not isinstance(args[0], cls):
                    raise TypeError
                result = op(getattr(self, attr), getattr(args[0], attr))
            else:
                result = op(getattr(self, attr))
            if isinstance(result, bool) or factory is None:
                return result
            return factory(self, result)

        return opfunc

    def __call__(self, cls):
        for opname in self.operators:
            opfname = '__%s__' % opname
            if opfname not in cls.__dict__:
                op = getattr(operator, opfname)
                setattr(cls, opfname, self._build_op(op, cls))
        return cls


class comparison_passthru(operator_passthru):
    operators = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']


class arithmetic_passthru(operator_passthru):
    operators = [
        'add', 'sub', 'mul', 'floordiv', 'mod', 'pow', 'lshift', 'rshift',
        'and', 'or', 'xor', 'div', 'truediv',

        'neg', 'pos', 'abs', 'invert',
    ]


class augmented_arithmetic_passthru(operator_passthru):
    operators = [
        'iadd', 'isub', 'imul', 'idiv', 'itruediv', 'ifloordiv', 'imod',
        'ipow', 'ilshift', 'irshift', 'iand', 'ixor', 'ior',
    ]


class conversion_passthru(operator_passthru):
    operators = [
        'complex', 'int', 'long', 'float', 'oct', 'hex', 'coerce'
    ]
