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


class CannotWield(PathfinderError):
    """
    Thrown when an object cannot be wielded as a weapon.
    """
    pass


class ObjectNotWieldable(CannotWield):
    default_msg = "Object not wieldable"


class InsufficientFreeHands(CannotWield):
    default_msg = "Insufficient free hands to wield object"


class HandNotAvailable(CannotWield):
    default_msg = "Specified hand is not free to wield a weapon"

    def __init__(self, msg='', hand=None):
        self.hand = hand
        super(HandNotAvailable, self).__init__(msg=msg)


class NotWielding(PathfinderError):
    """Thrown when performing an action with a weapon that is not wielded."""
    def __init__(self, msg='', obj=None):
        self.obj = obj
        super(NotWielding, self).__init__(msg=msg)