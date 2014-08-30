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


class RankNotFound(OrgError):
    pass


class DuplicateRank(OrgError):
    pass


class InvalidRank(OrgError):
    pass


class RankInUse(OrgError):
    pass


class GradeAlreadyExists(OrgError):
    pass


class GradeNotFound(OrgError):
    pass
