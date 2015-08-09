import logging

from mudsling.errors import FailedMatch, AmbiguousMatch

class Role(object):
    name = ""
    perms = set()

    def __init__(self, name):
        self.name = name
        self.perms = set()

    def __str__(self):
        return self.name

    def add_perm(self, perm):
        if perm not in self.perms:
            self.perms.add(perm)
            return True
        return False

    def remove_perm(self, perm):
        if perm in self.perms:
            self.perms.remove(perm)
            return True
        return False

    def has_perm(self, perm):
        return perm in self.perms

    def reset_perms(self, perms=()):
        self.perms = set(perms)


def create_default_roles(defaults):
    from mudsling import game
    for role_name, perms in defaults.iteritems():
        try:
            game.db.match_role(role_name)
            # From here, we do nothing, because it already exists.
        except FailedMatch:
            role = Role(role_name)
            role.reset_perms(perms)
            game.db.roles.append(role)
        except AmbiguousMatch:
            m = 'Cannot setup "%s" role: ambiguous match!'
            logging.warning(m, role_name)
            continue
