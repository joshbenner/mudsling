import os
import hashlib

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

