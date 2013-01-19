from mudsling.storage import StoredObject
from mudsling.server import game
from mudsling.errors import InvalidObject, CommandInvalid
from mudsling.misc import Password
from mudsling.parse import ParsedInput
from mudsling.match import match_objlist


class BaseObject(StoredObject):
    """
    The base class for all other objects. You may subclass this if you need an
    object without location or contents. You should use this instead of
    directly subclassing StoredObject.

    @cvar commands: Commands provided by this class. Classes, not instances.

    @ivar possessed_by: The Player who is currently possessing this object.
    """

    _transientVars = ['possessed_by']

    #: @type: set
    commands = set()

    #: @type: Player
    possessed_by = None

    def possess(self, player):
        # TODO: Refactor this into a property?
        self.dispossess()
        self.possessed_by = player

    def dispossess(self):
        self.possessed_by = None

    def matchObject(self, search, err=False):
        """
        A general object match for this object.

        @param search: The search string.
        @param err: If true, can raise search result errors.

        @return: set
        """
        # TODO: Literal object matching
        if search == 'me':
            return {self}

        return match_objlist(search, {self}, err=err)

    def processInput(self, raw, passedInput=None, err=True):
        """
        Parses raw input as a command from this object and executes the first
        matching command it can find.
        """
        input = passedInput or ParsedInput(raw, self)
        cmd = self.matchCommand(input)
        if cmd is not None:
            self.doCommand(input, self, cmd)
            return True
        if err:
            raise CommandInvalid(input)
        return False

    def matchCommand(self, input):
        """
        Match ParsedInput against the commands provided by this object.

        Objects can override this to get clever about how they advertise their
        commands to other objects.

        @param input: ParsedInput which is being used to match commands.
        @type input: ParsedInput

        @return: type
        """
        for cmd in self.commands:
            if cmd.matchParsedInput(input):
                return cmd
        return None

    def doCommand(self, input, obj, cmdClass):
        """
        Executes the given command on the specified command host as this
        object having generated the given input.
        """
        cmd = cmdClass(obj, input, self)
        cmd.execute()


class Object(BaseObject):
    """
    This should be the parent for most game objects. It is the object class
    that has location, and can contain other objects.

    @ivar location: The object in which this object is located.
    @type location: Object

    @ivar contents: The set of objects contained by this object.
    @type contents: set

    @ivar desc: The description of the object.
    @type desc: str
    """

    #: @type: Object
    location = None
    contents = set()
    desc = ""

    def matchObject(self, search, err=False):
        """
        @type search: str
        @return: set
        """
        matches = super(Object, self).matchObject(search, err=err)
        if matches:
            return matches

        if search == 'here' and self.location is not None:
            return {self.location}

        matches = match_objlist(search, self.contents, err=err)
        if matches:
            return matches

        matches = match_objlist(search, self.location.contents, err=err)
        if matches:
            return matches

        return set()

    def getDescription(self):
        """
        Allows objects to embellish/calculate/cache the effective description.
        """
        return self.desc

    def contentRemoved(self, what, destination):
        """
        Called if an object was removed from this object.

        @param what: The object that moved
        @type what: Object

        @param destination: Where the object went.
        @type destination: Object
        """

    def contentAdded(self, what, previous_location):
        """
        Called when an object is added to this object's contents.

        @param what: The object that was moved.
        @type what: Object

        @param previous_location: Where the moved object used to be.
        @type previous_location: Object
        """

    def objectMoved(self, moved_from, moved_to):
        """
        Called when this object was moved.

        @param moved_from: Where this used to be.
        @type moved_from: Object

        @param moved_to: Where this is now.
        @type moved_to: Object
        """

    def moveTo(self, dest):
        """
        Move the object to a new location. Updates contents on source and
        destination, and fires corresponding hooks on all involved.

        @param dest: Where to move the object. Can be None or Object.
        @type dest: Object

        Throws InvalidObject if this object is invalid or if the destination is
        neither None nor a valid Object instance.
        """
        if not game.db.isValid(self):
            raise InvalidObject(self)

        # We allow moving to None
        if dest is not None:
            if not game.db.isValid(dest):
                raise InvalidObject(dest, "Destination invalid")
            if not isinstance(dest, Object):
                raise InvalidObject(dest, "Destination is not a location")

        previous_location = self.location
        if isinstance(self.location, Object):
            self.location.contents.remove(self)

        self.location = dest

        if isinstance(dest, Object):
            dest.contents.add(self)

        # Now fire event hooks on the two locations and the moved object.
        if isinstance(previous_location, Object):
            previous_location.contentRemoved(self, dest)
        if isinstance(dest, Object):
            dest.contentAdded(self, previous_location)

        self.objectMoved(previous_location, dest)


class Player(BaseObject):
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
