

class Role(object):
    name = ""
    perms = set()

    def __init__(self, name):
        self.name = name
        self.perms = set()

    def __str__(self):
        return self.name

    def addPerm(self, perm):
        if perm not in self.perms:
            self.perms.add(perm)
            return True
        return False

    def removePerm(self, perm):
        if perm in self.perms:
            self.perms.remove(perm)
            return True
        return False

    def hasPerm(self, perm):
        return perm in self.perms
