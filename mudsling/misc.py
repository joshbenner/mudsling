import os
import hashlib
import re

import pbkdf2


class Password(object):
    """
    A password namedtuple. Creates a hash of the raw password in a manner that
    would make comparisons with other stored passwords useless, and pose some
    problems for traditional password cracking methods.

    @ivar algorithm: The algorithm used to hash the password.
    @ivar salt: The salt used in the hash.
    @ivar cost: The number of iterations in PBKDF2.
    @ivar hash: The resulting hash
    """

    algorithm = None
    salt = None
    cost = None
    hash = None

    def __init__(self, raw):
        # This should select the strongest algorithm available.
        self.algorithm = hashlib.algorithms[-1]

        hashfunc = getattr(hashlib, self.algorithm)
        self.salt = os.urandom(16).encode('hex')
        self.cost = 1000
        self.hash = pbkdf2.pbkdf2_hex(raw,
                                      self.salt,
                                      hashfunc=hashfunc,
                                      iterations=self.cost)

    def matchesPassword(self, password):
        """
        Tests if a password will generate the same hash, meaning the password
        is the same string used originally to generate the hash.

        @param password: The password to test.

        @return: bool
        """

        # To complete this test, we will generate a new hash based on the input
        # but using this objects other settings (salt, etc).

        # First, let's make sure we have the required hash function.
        if self.algorithm not in hashlib.algorithms:
            # We can't generate a hash to test, so fail.
            return False

        keylen = len(self.hash) / 2
        hash = pbkdf2.pbkdf2_hex(password,
                                 self.salt,
                                 hashfunc=getattr(hashlib, self.algorithm),
                                 iterations=self.cost,
                                 keylen=keylen)

        return hash == self.hash


class SyntaxParseError(Exception):
    pass


class Syntax(object):
    """
    Load a natural syntax spec and prepare for parsing!

        [ ] = Optional segment
        < > = User value (named). Values in parse dict with named keys.
        { } = Required from set. Values in parse dict with 'optset#' keys.

        User value spec:
            <name>[:<pattern>]
            ie: <userval:[0-9]+>
    """
    natural = None
    regex = None
    _compiled = None

    def __init__(self, syntax):
        self.natural = syntax
        self.regex = self.syntax_to_regex(syntax)
        self._compiled = re.compile(self.regex, re.I)

    def syntax_to_regex(self, syntax):
        regex = ['^']

        i = 0
        optsets = 0
        lastchar = ''
        while i < len(syntax):
            char = syntax[i]
            if char == '[':
                if lastchar == ' ':
                    # Optional group after a space. Include space
                    # in optional group.
                    regex = regex[:-2]
                    regex.extend(['(?:', ' ', '+'])
                else:
                    regex.append('(?:')
                    lastchar = ''
            elif char == ']':
                regex.append(')?')
                lastchar = ''
            elif char == '<':
                lastchar = ''
                end = syntax.find('>', i)
                if end == -1:
                    raise SyntaxParseError('Missing closing >')
                userval = syntax[i + 1:end]
                i = end
                name, sep, pat = userval.partition(':')
                if pat == '':
                    pat = '[^ ]+'
                regex.append('(?P<%s>%s)' % (name, pat))
            elif char == '{':
                lastchar = ''
                end = syntax.find('}', i)
                if end == -1:
                    raise SyntaxParseError('Missing closing }')
                opt_spec = syntax[i + 1:end]
                i = end
                opt_regexes = []
                for opt in [s.strip() for s in opt_spec.split('|')]:
                    opt_re = self.syntax_to_regex(opt).rstrip('$').lstrip('^')
                    opt_regexes.append(opt_re)
                optsets += 1
                regex.append('(?P<optset%d>' % optsets)
                regex.append('(?:%s))' % ')|(?:'.join(opt_regexes))
            else:
                if char == ' ' and lastchar == ' ':
                    pass
                else:
                    regex.append(char)
                    if char == ' ':
                        regex.append('+')
                    lastchar = char
            i += 1

        regex.append('$')
        return ''.join(regex)

    def parse(self, string):
        m = self._compiled.search(string)
        if m:
            return m.groupdict()
        return False
