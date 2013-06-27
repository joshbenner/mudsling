
from mudsling import errors


class PathfinderError(errors.Error):
    default_msg = ''

    def __init__(self, msg=''):
        msg = msg or self.default_msg
        super(PathfinderError, self).__init__(msg)


class CharacterError(PathfinderError):
    pass


class SkillError(CharacterError):
    pass
