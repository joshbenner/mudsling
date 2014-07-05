import mudsling.errors


class OrgError(mudsling.errors.Error):
    pass


class AlreadyInOrg(OrgError):
    pass


class NotInOrg(OrgError):
    pass