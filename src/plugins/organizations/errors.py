import mudsling.errors


class OrgError(mudsling.errors.Error):
    pass


class AlreadyInOrg(OrgError):
    pass


class NotInOrg(OrgError):
    pass


class RecursiveParentage(OrgError):
    pass


class AlreadyManager(OrgError):
    pass


class NotManager(OrgError):
    pass
