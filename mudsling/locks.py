"""
MUDSling lock system.

Inspired by Evennia's lock system.
"""

import logging

import pyparsing

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

    _transientVars = ['parsed']

    def __init__(self, lockStr):
        self.raw = lockStr

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
NonePass = Lock('False')  # Always False
AllPass = Lock('True')    # Always True


class LockSet(storage.Persistent):
    raw = ""
    locks = None

    _transientVars = ['locks']

    def __init__(self, lockSetStr=''):
        self.raw = lockSetStr

    def parse(self):
        locks = {}
        for lockStr in self.raw.split(';'):
            type, sep, lockStr = lockStr.partition(':')
            if type and lockStr:
                # todo: Raise error on invalid type/str pair?
                locks[type] = Lock(lockStr)
        self.locks = locks

    def hasType(self, type):
        if self.locks is None:
            self.parse()
        return type in self.locks

    @staticmethod
    def _compose(locks):
        """
        Composes a lock set string from the given dictionary of types/locks.

        @param locks: Dictionary of L{Lock} objects keyed by lock type.
        @type locks: C{dict}

        @return: A raw lock set string.
        @rtype: C{str}
        """
        return ';'.join(["%s:%s" % (type, lock.raw)
                         for type, lock in locks.iteritems()])

    def _init_locks(self):
        if self.locks is None:
            self.locks = {}

    def getLock(self, type):
        return self.locks[type] if self.hasType(type) else NonePass

    def setLock(self, type, lock):
        self._init_locks()
        if isinstance(lock, basestring):
            lock = Lock(lock)
        self.locks[type] = lock
        self.raw = self._compose(self.locks)

    def delLock(self, type):
        self._init_locks()
        if type in self.locks:
            del self.locks[type]
            self.raw = self._compose(self.locks)

    def delAll(self):
        self.raw = ""
        self.locks = {}

    def check(self, type, *args):
        return self.getLock(type).eval(*args)
