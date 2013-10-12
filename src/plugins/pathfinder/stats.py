from collections import OrderedDict

from mudsling.storage import Persistent

import dice


def resolve_roll_var(name, vars, state):
    """
    Implementation of dynamic variable name handling for diceroll evaluation.

    :param name: The variable name being sought.
    :param vars: The other variables participating in the roll evaluation.
    :param state: The roll evaluation state.

    :return: Tuple of value and roll description. Description can be None.
    """
    try:
        #: :type: HasStats
        obj = state['stat object']
        result = obj.get_stat(name.replace('_', ' '), desc=state['desc'])
        if state['desc']:
            result, desc = result
        else:
            desc = None
        return result, desc
    except KeyError:
        raise NameError("Variable '%s' not found" % name)


class HasStats(Persistent):
    """
    A persistent object with arbitrary stats.
    """
    stats = {}
    stat_defaults = {}
    stat_attributes = {}
    stat_aliases = {}
    _stat_cache = {}

    _dependent_data = {}

    # TODO: Should probably live somewhere else.
    def _build_dependent_data(self):
        """
        Utility method for building interdependent sets of data.
        """
        meta = self._dependent_data
        done = dict(zip(meta.keys(), (False,) * len(meta)))
        count = dict(zip(meta.keys(), (0,) * len(meta)))
        data = dict((k, meta[k]['start'](self)) for k in meta.iterkeys())
        while not all(done.itervalues()):
            for name, info in meta.iteritems():
                if len(data[name]) > count[name]:
                    func = getattr(self, info['process'])
                    func(data[name][count[name]:], data)
                    count[name] = len(data[name])
                else:
                    done[name] = True
        for name, info in meta.iteritems():
            if 'cache' in info:
                self.cache_stat(info['cache'], data[name])

    @classmethod
    def _stats_mro(cls):
        return [c for c in cls.__mro__ if issubclass(c, HasStats)]

    def get_stat_default(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
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
        name = name.lower()
        for cls in self.__class__._stats_mro():
            if 'stat_aliases' in cls.__dict__ and name in cls.stat_aliases:
                return cls.stat_aliases[name], ()
        return name.lower(), ()

    def get_stat_base(self, stat, resolved=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat in self.stats:
            return self.stats[stat]
        return self.get_stat_default(stat)

    def get_stat_modifiers(self, stat):
        """
        Retrieve any modifiers (static values or rolls) which currently apply
        to the specific stat.

        Default implementation returns no modifiers. Children should override.

        :return: Ordered collection of keys describing the source of the
            modifier, and values representing value modifiers for the stat.
            Modifiers may be static values or rolls/expressions.
        :rtype: collections.OrderedDict
        """
        return OrderedDict()

    def get_all_stat_names(self):
        """
        Retrieve a set of all stat names.
        :rtype: set
        """
        stats = set()
        if 'stats' in self.__dict__:
            stats.update(self.stats.iterkeys())
        for cls in self._stats_mro():
            if 'stat_defaults' in cls.__dict__:
                stats.update(cls.stat_defaults.iterkeys())
        return stats

    def get_stat(self, stat, resolved=False, desc=False):
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        if stat in self._stat_cache:
            cached = self._stat_cache[stat]
            if isinstance(cached, list):
                if not desc:
                    return sum(map(self._eval_stat_part, cached))
                else:
                    results = []
                    desc_parts = []
                    for part in cached:
                        r, d = self._eval_stat_part(part, desc=True)
                        results.append(r)
                        desc_parts.append(d)
                    return sum(results), ' + '.join(desc_parts)
            elif desc:
                return cached, "%s(%s)" % (stat, cached)
            else:
                return cached
        # low, high = self.get_stat_limits(stat)
        # if low == high:  # Only ever a single result.
        #     self.cache_stat(stat, low)
        # else:
        # Cache the base and all modifiers in a single list to be summed.
        parts = [(stat, self.get_stat_base(stat))]
        #parts.extend(self.get_stat_modifiers(stat).itervalues())
        parts.extend((str(source), mod) for source, mod
                     in self.get_stat_modifiers(stat).iteritems())
        self.cache_stat(stat, parts)
        return self.get_stat(stat, desc=desc)

    def cache_stat(self, stat, value):
        if '_stat_cache' not in self.__dict__:
            self._stat_cache = {}
        self._stat_cache[stat] = value

    def clear_stat_cache(self, key=None):
        if key is not None:
            if key in self._stat_cache:
                del self._stat_cache[key]
        else:
            self._stat_cache = {}

    def get_stat_limits(self, stat, resolved=False):
        """
        Retrieve the minimum and maximum of a stat.
        """
        if '_stat_cache' not in self.__dict__:
            self._stat_cache = {}
        cache = self._stat_cache
        stat = stat if resolved else self.resolve_stat_name(stat)[0]
        key = '%s|limits' % stat
        if key in cache:
            return cache[key]
        low, high = self._eval_stat_part(self.get_stat_base(stat), limits=True)
        for part in self.get_stat_modifiers(stat).itervalues():
            l, h = self._eval_stat_part(part, limits=True)
            low += l
            high += h
        cache[key] = (low, high)
        return low, high

    def _eval_stat_part(self, part, limits=False, desc=False):
        name = '?'
        if isinstance(part, tuple):
            name, part = part
        if isinstance(part, basestring):
            roll = dice.Roll(part)
        elif isinstance(part, dice.Roll):
            roll = part
        else:
            if part is None:
                part = 0
            if limits:
                return part, part
            elif desc:
                return part, '%s(%s)' % (name, part)
            else:
                return part
        return self.roll_limits(roll) if limits else self.roll(roll, desc=desc)

    def roll(self, roll, desc=False, state=None, **vars):
        """Calculate the results of rolls and stats.

        :param roll: The roll expression to evaluate.
        :type roll: basestring or dice.Roll

        :param desc: Whether or not to include the details of how the result
            was calculated. Useful to show to users.
        :type desc: bool

        :param state: The state dictionary to pass to the roll. Useful when
            complex information needs to be passed into or out of the roll.
        :type state: dict or None

        :param vars: Variables to make available to the roll expression.
        :type vars: dict

        :return: A tuple of result value and description (if desc enabled), or
            just the result value.
        :rtype: tuple or int or float
        """
        state = state or {}
        if isinstance(roll, basestring):
            roll = dice.Roll(roll)
        vars['__var'] = resolve_roll_var
        state['stat object'] = self
        state['desc'] = desc
        result, d = roll._eval(vars, state)
        if isinstance(result, list):
            result = sum(result)
        return (result, d) if desc else result

    def roll_limits(self, roll, state=None, **vars):
        """
        Similar to :method:`HasStats.roll`, but the lower and upper bounds of
        the possible result values are returned instead of performing a normal
        evaluation of the roll expression.

        :param roll: A roll expression to evaluate.
        :type roll: basestring or dice.Roll
        :param state: A state dictionary to pass into roll evaluation.
        :type state: dict or None
        :param vars: Variables to make available to the roll evaluation.
        :type vars: dict

        :return: A tuple of lower and upper bounds of possible results.
        :rtype: tuple
        """
        state = state or {}
        if isinstance(roll, basestring):
            roll = dice.Roll(roll)
        vars['__var'] = resolve_roll_var
        state['stat object'] = self
        return roll.limits(vars, state)

    def set_stat(self, stat, val):
        if 'stats' not in self.__dict__:
            self.stats = {}
        self.clear_stat_cache()
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
