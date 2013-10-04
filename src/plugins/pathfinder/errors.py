
import mudsling.errors


class PathfinderError(mudsling.errors.Error):
    default_msg = ''

    def __init__(self, msg=''):
        msg = msg or self.default_msg
        super(PathfinderError, self).__init__(msg)


class DataNotFound(PathfinderError):
    pass


class DataNotReady(PathfinderError):
    """
    Thrown when an operation is attempted that requires the Pathfinder data to
    be loaded when it is not yet all loaded.
    """
    pass


class InvalidModifierType(PathfinderError):
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


class InvalidContent(mudsling.errors.MoveDenied):
    pass


class DoesNotFit(mudsling.errors.MoveDenied):
    pass
