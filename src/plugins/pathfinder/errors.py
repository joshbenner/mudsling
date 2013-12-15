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


class CannotWield(PathfinderError):
    """
    Thrown when an object cannot be wielded as a weapon.
    """
    pass


class ObjectNotWieldable(CannotWield):
    default_msg = "Object not wieldable"


class AlreadyWielding(CannotWield):
    default_msg = "Object already wielded"


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


class NoSuchAttack(PathfinderError):
    """
    Thrown when attempting an attack with a weapon that does not support it.
    """
    pass


class PartNotFoundError(mudsling.errors.Error):
    """
    Thrown when a specified part isn't found on a MultipartThing.
    """
    pass


class OutOfAttackRange(PathfinderError):
    default_msg = "Target is out of attack range"


class InvalidSave(PathfinderError):
    """
    Thrown when a specified save type is invalid.
    """
    pass


class InsufficientAmmo(PathfinderError):
    """
    Thrown if a weapon lacks ammunition.
    """
    pass
