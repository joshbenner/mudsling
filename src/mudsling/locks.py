"""
MUDSling lock system.

Inspired by Evennia's lock system.
"""

import logging

from mudsling import storage

from mudsling import utils
import mudsling.utils.locks


# Parser cache. Since we only intend to have a single parser, we avoid re-
# generating it every time we need it. Code can access this directly if it is
# confident the Parser is already generated.
Parser = None


def parser(funcs=None, cache=True, reset=False):
    """
    Canonical function for obtaining the parser instance. If the code *knows*
    the Parser has already been generated, it can access Parser directly. You
    can also get one-off parsers by passing cache=False.

    @param funcs: Funciton map for use by the parser. Due to cache, this can
        usually be omitted, unless this is the first call or the parser is
        being regenerated for some reason.
    @type funcs: C{dict}

    @param cache: If True, will cache the parser as the default parser.
    @type cache: C{bool}

    @param reset: If True, will regenerate the parser.
    @type reset: C{bool}

    @return: Lock parser.
    """
    global Parser

    if cache and not reset and Parser is not None:
        return Parser

    funcs = funcs or {}
    p = utils.locks.LockParser(funcs)
    if cache:
        Parser = p
    return p


class Lock(storage.Persistent):
    raw = ""

    #: @type: L{mudsling.utils.locks.LockFunc}
    parsed = None

    _transient_vars = ['parsed']

    def __init__(self, lockStr):
        self.raw = lockStr

    def __str__(self):
        return self.raw

    def __repr__(self):
        return "Lock('%s')" % self.raw

    def parse(self, parser=None):
        """
        Parses .raw to populate .parsed. Assumes Parser is already generated.
        """
        if parser is None:
            parser = Parser
        self.parsed = None
        if self.raw.lower() == 'true':
            self.parsed = True
        elif self.raw.lower() == 'false':
            self.parsed = False
        else:
            try:
                self.parsed = parser.parseString(self.raw, parseAll=True)[0]
            except utils.locks.ParseException as e:
                logging.error("Error parsing lock: %r\n  %s",
                              self.raw, e.message)

    def eval(self, *args):
        if self.parsed is None:
            self.parse()
        if isinstance(self.parsed, bool):
            return self.parsed
        else:
            return self.parsed.eval(*args)


# Lock identities.
none_pass = Lock('False')  # Always False
all_pass = Lock('True')    # Always True


class LockSet(storage.Persistent):
    raw = ""
    locks = None

    _transient_vars = ['locks']

    def __init__(self, lockSetStr=''):
        self.raw = lockSetStr

    def __str__(self):
        return self.raw

    def __repr__(self):
        return "Lock('%s')" % self.raw

    def parse(self):
        locks = {}
        for lockStr in self.raw.split(';'):
            lockType, sep, lockStr = lockStr.partition(':')
            if lockType and lockStr:
                # todo: Raise error on invalid type/str pair?
                locks[lockType] = Lock(lockStr)
        self.locks = locks

    def has_type(self, lockType):
        if self.locks is None:
            self.parse()
        return lockType in self.locks

    @staticmethod
    def _compose(locks):
        """
        Composes a lock set string from the given dictionary of types/locks.

        @param locks: Dictionary of L{Lock} objects keyed by lock type.
        @type locks: C{dict}

        @return: A raw lock set string.
        @rtype: C{str}
        """
        return ';'.join(["%s:%s" % (lockType, lock.raw)
                         for lockType, lock in locks.iteritems()])

    def _init_locks(self):
        if self.locks is None:
            self.locks = {}

    def get_lock(self, lockType):
        return self.locks[lockType] if self.has_type(lockType) else none_pass

    def set_lock(self, lockType, lock):
        self._init_locks()
        if isinstance(lock, basestring):
            lock = Lock(lock)
        self.locks[lockType] = lock
        self.raw = self._compose(self.locks)

    def del_lock(self, lockType):
        self._init_locks()
        if lockType in self.locks:
            del self.locks[lockType]
            self.raw = self._compose(self.locks)

    def del_all(self):
        self.raw = ""
        self.locks = {}

    def check(self, lockType, *args):
        return self.get_lock(lockType).eval(*args)
