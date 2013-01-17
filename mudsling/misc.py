import os
from collections import namedtuple
import hashlib

import pbkdf2


class Password(namedtuple('Passwd', 'algorithm, salt, cost, hash')):
    """
    A password namedtuple. Creates a hash of the raw password in a manner that
    would make comparisons with other stored passwords useless, and pose some
    problems for traditional password cracking methods.
    """

    def __new__(cls, raw):
        # This should select the strongest algorithm available.
        algorithm = hashlib.algorithms[-1]

        hashfunc = getattr(hashlib, algorithm)
        salt = os.urandom(16).encode('hex')
        cost = 1000
        hash = pbkdf2.pbkdf2_hex(raw, salt, hashfunc=hashfunc, iterations=cost)

        return super(Password, cls).__new__(cls, algorithm, salt, cost, hash)

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
