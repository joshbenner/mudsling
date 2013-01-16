from mudsling.storage import Persistent


class Object(Persistent):
    """
    Base class for all game-world objects.

    @ivar id: The unique object ID for this object in the game.
    @type id: int
    """

    id = None

    def __init__(self):
        """
        Initialization at this level is only run when the object is first
        created. Loading from the DB does not call __init__.
        """
