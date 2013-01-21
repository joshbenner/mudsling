

class Role(object):
    name = ""
    perms = set()

    def __init__(self, name):
        self.name = name
        self.perms = set()

    def __str__(self):
        return "Role: %s" % self.name

    def addPerm(self, perm):
        if perm not in self.perms:
            self.perms.add(perm)

    def removePerm(self, perm):
        if perm in self.perms:
            self.perms.remove(perm)

    def hasPerm(self, perm):
        return perm in self.perms
