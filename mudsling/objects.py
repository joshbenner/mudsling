from mudsling.storage import StoredObject
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

    @ivar possessed_by: The BasePlayer who is currently possessing this object.
    @ivar possessable_by: List of players who can possess this object.
    @ivar roles: The set of roles granted to this object. For most objects,
        this variable will always be empty. Characters and especially players,
        however, may have occasion to be granted roles.
    """

    _transientVars = ['possessed_by']

    #: @type: set
    commands = set()

    #: @type: BasePlayer
    possessed_by = None

    possessable_by = []

    roles = set()

    def possessableBy(self, player):
        """
        Returns True if the player can possess this object.
        @param player: The player.
        @return: bool
        """
        return (player in self.possessable_by
                or player.hasPerm("possess anything"))

    def possessBy(self, player):
        # TODO: Refactor this into a property?
        if self.possessed_by is not None:
            self.possessed_by.dispossessObject(self)
        self.possessed_by = player
        self.onPossessed(player)

    def dispossessed(self):
        """
        Called after this object has been dispossessed by a BasePlayer.
        """
        previous = self.possessed_by
        self.possessed_by = None
        if previous is not None:
            self.onDispossessed(previous)

    def onPossessed(self, player):
        """
        Event hook called when this object has been possessed by a BasePlayer.
        @param player: BasePlayer which has possessed the object.
        @type player: BasePlayer
        """

    def onDispossessed(self, player):
        """
        Event hook called when this object has been dispossessed by a BasePlayer.
        @param player: The player that previously possessed this object.
        @type player: BasePlayer
        """

    def matchObject(self, search, err=False):
        """
        A general object match for this object.

        @param search: The search string.
        @param err: If true, can raise search result errors.

        @rtype: set
        """
        # TODO: Literal object matching
        if search == 'me':
            return {self}

        return match_objlist(search, {self}, err=err)

    def processInput(self, raw, passedInput=None, err=True):
        """
        Parses raw input as a command from this object and executes the first
        matching command it can find.

        The passedInput and err parameters help accommodate children overriding
        this method without having to jump through more hoops than needed.
        """
        input = passedInput or ParsedInput(raw, self)
        for obj in self.commandHosts(input):
            cmd = obj.matchCommand(input)
            if cmd is not None:
                self.doCommand(input, obj, cmd)
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

        @rtype: type
        """
        for cmd in self.commands:
            if cmd.matchParsedInput(input):
                return cmd
        return None

    def commandHosts(self, input):
        """
        Given ParsedInput, return a list of objects which will be checked, in
        order, for a command matching the input. The input is assumed to have
        come from this object.

        @param input: The ParsedInput from which to generate the list.
        @type input: ParsedInput

        @rtype: list
        """
        hosts = [self]
        if input.dobj is not None:
            hosts.append(input.dobj)
        if input.iobj is not None:
            hosts.append(input.iobj)

        return hosts

    def doCommand(self, input, obj, cmdClass):
        """
        Executes the given command on the specified command host as this
        object having generated the given input.
        """
        cmd = cmdClass(obj, input, self)
        cmd.execute()

    def hasPerm(self, perm):
        """
        Checks if this object has the permission specified. An object has a
        perm if it has a role in which that permission can be found.
        """
        for role in self.roles:
            if perm in role.perms:
                return True
        return False

    def hasRole(self, role):
        return role in self.roles

    def addRole(self, role):
        if role not in self.roles:
            self.roles.add(role)

    def removeRole(self, role):
        if role in self.roles:
            self.roles.remove(role)


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
        @rtype: set
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

    def commandHosts(self, input):
        """
        Add the object's location after self.
        @rtype: list
        """
        hosts = super(Object, self).commandHosts(input)
        if self.location is not None:
            hosts.insert(1, self.location)

        return hosts

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
        if not self.db.isValid(self):
            raise InvalidObject(self)

        # We allow moving to None
        if dest is not None:
            if not self.db.isValid(dest):
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


class BasePlayer(BaseObject):
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

    #: @type: BaseObject
    possessing = None

    def __init__(self, name, password, email):
        super(BasePlayer, self).__init__()
        self.name = name
        self.password = Password(password)
        self.email = email

    def sessionAttached(self, session):
        if self.session is not None:
            # This should result in self.sessionDetached() being called
            # which will free up self.session
            self.session.disconnect("BasePlayer taken over by another connection")
        else:
            # TODO: BasePlayer is connecting. Should we tell someone?
            pass
        self.session = session

    def sessionDetached(self, session):
        """
        Called by a session that thinks it is connected to this player upon
        disconnect.
        """
        if self.session == session:
            self.session = None

    def possessObject(self, obj):
        obj.possessBy(self)
        if obj.possessed_by == self:
            self.possessing = obj
            self.onObjectPossessed(obj)

    def dispossessObject(self, obj):
        if self.possessing == obj:
            self.possessing = None
            obj.dispossessed()
            self.onObjectDispossessed(obj)

    def onObjectPossessed(self, obj):
        """
        Event hook that fires right after BasePlayer has possessed an object.
        @param obj: The object that is now possessed by the player.
        @type obj: BaseObject
        """

    def onObjectDispossessed(self, obj):
        """
        Event hook that fires right after BasePlayer has dispossessed an object.
        @param obj: The object that was previously possessed.
        @type obj: BaseObject
        """


class BaseCharacter(Object):
    pass
