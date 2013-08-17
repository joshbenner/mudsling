
from mudsling import errors


class PathfinderError(errors.Error):
    default_msg = ''

    def __init__(self, msg=''):
        msg = msg or self.default_msg
        super(PathfinderError, self).__init__(msg)


class DataNotFound(PathfinderError):
    pass


class CharacterError(PathfinderError):
    pass


class SkillError(CharacterError):
    pass


class InvalidSubtype(PathfinderError):
    def __init__(self, msg='', feat_class=None, subtype=''):
        super(InvalidSubtype, self).__init__(msg)
        self.feat_class = feat_class
        self.subtype = subtype
