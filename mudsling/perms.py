

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
