from mudsling.storage import GameObject
from mudsling.server import game
from mudsling.errors import InvalidObject
from mudsling.misc import Password
from mudsling.parse import ParsedInput


class Object(GameObject):
    """
    The base class for all other objects. You may subclass this if you need an
    object without location or contents. You should use this instead of
    directly subclassing GameObject.

    @ivar possessed_by: The Player who is currently possessing this object.
    """

    _transientVars = ['possessed_by']

    #: @type: Player
    possessed_by = None

    def possess(self, player):
        # TODO: Refactor this into a property?
        self.dispossess()
        self.possessed_by = player

    def dispossess(self):
        self.possessed_by = None

    def parseInput(self, raw):
        """
        Parses raw input as a command from this object.
        """
        input = ParsedInput(raw)
        cro = self.commandResolutionOrder()
        # TODO: Concept of 'context' used for both matching AND command search?

    def commandResolutionOrder(self):
        """
        Build the set of objects on which commands can be found and executed
        by this object.

        @return: set
        """
        return {self}


class PhysicalObject(Object):
    """
    This should be the parent for most game objects. It is the object class
    that has location, and can contain other objects.

    @ivar location: The object in which this object is located.
    @type location: PhysicalObject

    @ivar contents: The set of objects contained by this object.
    @type contents: set

    @ivar desc: The description of the object.
    @type desc: str
    """

    #: @type: PhysicalObject
    location = None
    contents = set()
    desc = ""

    def commandResolutionOrder(self):
        cro = super(PhysicalObject, self).commandResolutionOrder()

        cro |= self.contents

        if self.location is not None:
            cro.add(self.location)
            cro |= self.location.contents

        return cro

    def getDescription(self):
        """
        Allows objects to embellish/calculate/cache the effective description.
        """
        return self.desc

    def contentRemoved(self, what, destination):
        """
        Called if an object was removed from this object.

        @param what: The object that moved
        @type what: PhysicalObject

        @param destination: Where the object went.
        @type destination: PhysicalObject
        """

    def contentAdded(self, what, previous_location):
        """
        Called when an object is added to this object's contents.

        @param what: The object that was moved.
        @type what: PhysicalObject

        @param previous_location: Where the moved object used to be.
        @type previous_location: PhysicalObject
        """

    def objectMoved(self, moved_from, moved_to):
        """
        Called when this object was moved.

        @param moved_from: Where this used to be.
        @type moved_from: PhysicalObject

        @param moved_to: Where this is now.
        @type moved_to: PhysicalObject
        """

    def moveTo(self, dest):
        """
        Move the object to a new location. Updates contents on source and
        destination, and fires corresponding hooks on all involved.

        @param dest: Where to move the object. Can be None or PhysicalObject.
        @type dest: PhysicalObject

        Throws InvalidObject if this object is invalid or if the destination is
        neither None nor a valid PhysicalObject instance.
        """
        if not game.db.isValid(self):
            raise InvalidObject(self)

        # We allow moving to None
        if dest is not None:
            if not game.db.isValid(dest):
                raise InvalidObject(dest, "Destination invalid")
            if not isinstance(dest, PhysicalObject):
                raise InvalidObject(dest, "Destination is not a location")

        previous_location = self.location
        if isinstance(self.location, PhysicalObject):
            self.location.contents.remove(self)

        self.location = dest

        if isinstance(dest, PhysicalObject):
            dest.contents.add(self)

        # Now fire event hooks on the two locations and the moved object.
        if isinstance(previous_location, PhysicalObject):
            previous_location.contentRemoved(self, dest)
        if isinstance(dest, PhysicalObject):
            dest.contentAdded(self, previous_location)

        self.objectMoved(previous_location, dest)


class Player(Object):
    """
    Base player class.

    Players are essentially 'accounts' that are connected to sessions. They can
    then possess other objects (usually Characters).

    @ivar password: The hash of the password used to login to this player.
    @ivar email: The player's email address.
    @ivar session: The session object connected to this player.
    """

    _transientVars = ['session']
    session = None

    #: @type: Password
    password = None

    #: @type: str
    email = ""

    def __init__(self, name, password, email):
        super(Player, self).__init__()
        self.name = name
        self.password = Password(password)
        self.email = email
