from collections import OrderedDict

from mudsling.storage import Persistent

import dice


def resolve_roll_var(name, vars, state):
    """
    Implementation of dynamic variable name handling for diceroll evaluation.

    @param name: The variable name being sought.
    @param vars: The other variables participating in the roll evaluation.
    @param state: The roll evaluation state.

    @return: Tuple of value and roll description. Description can be None.
    """
    try:
        return state['stat object'].get_stat(name.replace('_', ' ')), None
    except KeyError:
        raise NameError("Variable '%s' not found" % name)


class HasStats(Persistent):
    """
    A persistent object with arbitrary stats.
    """
    stats = {}
    stat_defaults = {}
    stat_attributes = {}

    @classmethod
    def _stats_mro(cls):
        return [c for c in cls.__mro__ if issubclass(c, HasStats)]

    def get_stat_default(self, stat):
        for c in self._stats_mro():
            if 'stat_defaults' in c.__dict__ and stat in c.stat_defaults:
                return c.stat_defaults[stat]
        raise KeyError("No default for stat '%s'" % stat)

    def stat_name_from_attribute(self, attr):
        """
        Given an atribute name, find the mapped stat.
        """
        for c in self._stats_mro():
            if 'stat_attributes' in c.__dict__ and attr in c.stat_attributes:
                return c.stat_attributes[attr]
        return None

    def resolve_stat_name(self, name):
        """
        Takes a stat name and resolves it to its canonical name and any tags
        implied by the original name.
        """
        return name.lower(), ()

    def get_stat_base(self, stat):
        stat = self.resolve_stat_name(stat)[0]
        if stat in self.stats:
            return self.stats[stat]
        return self.get_stat_default(stat)

    def get_stat_modifiers(self, stat):
        """
        Retrieve any modifiers (static values or rolls) which currently apply
        to the specific stat.

        Default implementation returns no modifiers. Children should override.

        @return: Ordered collection of keys describing the source of the
            modifier, and values representing value modifiers for the stat.
            Modifiers may be static values or rolls/expressions.
        @rtype: L{collections.OrderedDict}
        """
        return OrderedDict()

    def get_all_stat_names(self):
        """
        Retrieve a set of all stat names.
        @rtype: C{set}
        """
        stats = set()
        if 'stats' in self.__dict__:
            stats.update(self.stats.iterkeys())
        for cls in self._stats_mro():
            if 'stat_defaults' in cls.__dict__:
                stats.update(cls.stat_defaults.iterkeys())
        return stats

    def get_stat(self, stat):
        """
        Evaluate the stat and return the result.
        """
        base = self._eval_stat_part(self.get_stat_base(stat))
        return base + sum(map(self._eval_stat_part,
                              self.get_stat_modifiers(stat).itervalues()))

    def _eval_stat_part(self, part):
        if part is None:
            return 0
        elif isinstance(part, basestring):
            roll = dice.Roll(part)
        elif isinstance(part, dice.Roll):
            roll = part
        else:
            return part
        return self.roll(roll)

    def roll(self, roll, desc=False, state=None, **vars):
        state = state or {}
        if isinstance(roll, basestring):
            roll = dice.Roll(roll)
        vars['__var'] = resolve_roll_var
        state['stat object'] = self
        state['desc'] = desc
        result, d = roll._eval(vars, state)
        return (result, d) if desc else result

    def set_stat(self, stat, val):
        if 'stats' not in self.__dict__:
            self.stats = {}
        self.stats[stat] = val

    def __getattr__(self, item):
        stat = self.stat_name_from_attribute(item)
        if stat is not None:
            return self.get_stat(stat)
        else:
            try:
                # Another child of Persistent later in the ancestry could
                # define __getattr__, so give them an opportunity.
                # noinspection PyUnresolvedReferences
                return super(HasStats, self).__getattr__(item)
            except AttributeError as e:
                if '__getattr__' in e.message:
                    raise AttributeError("'%s' object has no attribute '%s'"
                                         % (self.__class__.__name__, item))
                else:
                    raise
