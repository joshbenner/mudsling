import inspect
import re

import zope.interface

from mudsling.storage import StoredObject, ObjRef
from mudsling import errors
from mudsling import locks
from mudsling import registry
from mudsling.match import match_objlist, match_stringlists
from mudsling.sessions import IInputProcessor
from mudsling.messages import IHasMessages, Messages
from mudsling.commands import IHasCommands

from mudsling import utils
import mudsling.utils.password
import mudsling.utils.input
import mudsling.utils.sequence
import mudsling.utils.object
import mudsling.utils.string
import mudsling.utils.email


class LockableObject(StoredObject):
    """
    Object that can have locks associated with it.

    @cvar createLock: The lock that must be satisfied to create an instance.

    @ivar locks: The general lockset provided by the instance. Class values may
        be scanned by self.getLock().
    """

    #: @type: locks.Lock
    createLock = locks.NonePass

    #: @type: locks.LockSet
    locks = locks.LockSet()

    def __init__(self, **kwargs):
        super(LockableObject, self).__init__(**kwargs)
        self.locks = locks.LockSet()

    def allows(self, who, op):
        """
        Determine if C{who} is allowed to perform C{op}. Superusers and objects
        they possess skip the check entirely. If C{who} has C{control} access,
        then they are a superuser for this object.

        @param who: The object attempting the operation.
        @type who: L{PossessableObject} or L{BasePlayer}

        @param op: The operation (lock type) being checked.
        @type op: C{str}

        @rtype: C{bool}
        """
        if who.player is not None and who.player.superuser:
            return True
        return (self.getLock(op).eval(self, who)
                or self.getLock('control').eval(self, who))

    def getLock(self, lockType):
        """
        Look for lock on object. If it's not there, ascend the object's MRO
        looking for a default.

        If no lock is found, then a Lock that always fails will be returned.

        @param lockType: The lock type to retrieve.
        @type lockType: C{str}

        @rtype: L{mudsling.locks.Lock}
        """
        if (isinstance(self.locks, locks.LockSet)
                and self.locks.hasType(lockType)):
            return self.locks.getLock(lockType)
        for cls in utils.object.ascendMro(self):
            if (hasattr(cls, "locks") and isinstance(cls.locks, locks.LockSet)
                    and cls.locks.hasType(lockType)):
                return cls.locks.getLock(lockType)
        return locks.NonePass


class NamedObject(LockableObject):
    """
    An object with names and can discern the names of other NamedObjects.

    @ivar _names: Tuple of all names this object is known by. First name is the
        primary name.
    """
    _names = ()

    def __init__(self, **kwargs):
        super(NamedObject, self).__init__(**kwargs)
        clsName = self.className()
        self.setNames(kwargs.get('names', ("New " + clsName, clsName)))

    def __str__(self):
        return self.name

    @property
    def name(self):
        """
        @rtype: str
        """
        return self._names[0]

    @property
    def aliases(self):
        return self._names[1:]

    @property
    def names(self):
        return self._names

    @property
    def nn(self):
        """
        Return the object's name and database ID.
        @rtype: str
        """
        return "%s (#%d)" % (self.name, self.objId)

    def _setNames(self, name=None, aliases=None, names=None):
        """
        Low-level method for maintaining the object's names. Should only be
        called by setName or setAliases.

        @param name: The new name. If None, do not change name.
        @param aliases: The new aliases. If None, do not change aliases.
        @param names: All names in one shot. If not None, other parameters are
            ignored and only this paramter is used.
        @return: Old names tuple.
        @rtype: C{tuple}
        """
        oldNames = self._names
        newNames = list(oldNames)
        if names is not None:
            if isinstance(names, tuple) or isinstance(names, list):
                newNames = list(names)
            else:
                raise TypeError("Names must be list or tuple.")
        else:
            if name is not None:
                # May be empty, so splice insert/set.
                newNames[0:1] = [str(name)]
            if isinstance(aliases, tuple) or isinstance(aliases, list):
                newNames[1:] = [str(a) for a in aliases]
        newNames = tuple(newNames)
        if newNames != oldNames:
            for n in newNames:
                if not isinstance(n, basestring):
                    raise TypeError("Names and aliases must be strings.")
            self._names = newNames
        return oldNames

    def setName(self, name):
        """
        Canonical method for changing the object's name. Children can override
        to attach other logic/actions to name changes.

        @param name: The new name.
        @return: The old name.
        """
        oldNames = self._setNames(name=name)
        return oldNames[0] if oldNames else None

    def setAliases(self, aliases):
        """
        Canonical method fo changing the object's aliases. Children can
        override to attach other logic/actions to alias changes.

        @param aliases: The new aliases.
        @type aliases: C{list} or C{tuple}
        @return: The old aliases.
        """
        return self._setNames(aliases=aliases)[1:]

    def setNames(self, names):
        """
        Sets name and aliases is one shot, using a single list or tuple where
        the first element is the name, and the other elements are the aliases.

        @param names: The new names to use.
        @return: Old names.
        """
        oldNames = self.names
        self.setName(names[0])
        self.setAliases(names[1:])
        return oldNames

    def namesFor(self, obj):
        """
        Returns a list of names representing the passed object as known by
        self. Default implementation is to just return all aliases.

        @param obj: The object whose "known" names to retrieve.
        @type obj: L{NamedObject} or L{ObjRef}
        @rtype: C{list}
        """
        try:
            return obj.names
        except (TypeError, AttributeError):
            return []

    def nameFor(self, obj):
        """
        Returns a string representation of the given object as known by self.

        @param obj: The object to name.
        @type obj: L{NamedObject} or L{ObjRef}

        @return: String name of passed object as known by this object.
        @rtype: C{str}
        """
        return (self.namesFor(obj) or ["UNKNOWN"])[0]


class PossessableObject(NamedObject):
    """
    An object which can be possessed by a player.

    @ivar possessed_by: The L{BasePlayer} who is currently possessing this obj.
    @ivar possessable_by: List of players who can possess this object.
    """

    #: @type: BasePlayer
    possessed_by = None

    #: @type: list
    possessable_by = []

    def __init__(self, **kwargs):
        super(PossessableObject, self).__init__(**kwargs)
        self.possessable_by = []

    @property
    def player(self):
        """
        Return ObjRef to the player object possessing this object.
        @rtype: BasePlayer or ObjRef
        """
        if self.possessed_by is not None:
            return self.possessed_by.player
        return None

    def possessableBy(self, player):
        """
        Returns True if the player can possess this object.
        @param player: The player.
        @return: bool
        """
        return (player in self.possessable_by
                or player.hasPerm("possess anything"))

    def possessBy(self, player):
        """
        Become possessed by a player.
        @param player: The player possessing this object.
        @type player: BasePlayer
        """
        # TODO: Refactor this into a property?
        if self.possessed_by is not None:
            self.possessed_by.dispossessObject(self.ref())
        self.possessed_by = player
        self.onPossessed(player)

    def dispossessed(self):
        """
        Called after this object has been dispossessed by a BasePlayer.
        """
        previous = self.possessed_by
        del self.possessed_by
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
        Event hook called when this object has been dispossessed by a player.
        @param player: The player that previously possessed this object.
        @type player: BasePlayer
        """

    def hasPerm(self, perm):
        """
        Returns True if the player possessing this object has the passed perm.
        """
        return self.player.hasPerm(perm) if self.player is not None else False

    def tell(self, *parts):
        """
        "Tells" the object a multi-part message. A shortcut for: .msg([...]).
        """
        self.msg(parts)

    def msg(self, text, flags=None):
        """
        Primary method of emitting text to an object (and any players/sessions
        which are attached to it).

        @param text: The text to send to the object.
        @type text: C{str} or C{list} or c{tuple}

        @param flags: Flags to modify how text is handled.
        """
        if self.possessed_by is not None:
            self.possessed_by.msg(self._format_msg(text), flags=flags)

    def _format_msg(self, parts):
        """
        Process a list of message parts into the final str message to send to
        object via .msg().

        Default conversions:
        * ObjRef, StoredObject -> self.nameFor(obj)

        @param parts: List of values to interpret into the message text.
        @type parts: list or str

        @rtype: str
        """
        if parts is None:
            return None
        if isinstance(parts, basestring):
            return parts
        parts = list(parts)
        for i, part in enumerate(parts):
            if self.db.isValid(part, StoredObject):
                # Other children of StoredObject might be compatible with the
                # nameFor method? Shows "UNKNOWN" if not.
                parts[i] = self.nameFor(part)
        return ''.join(map(str, parts))

    def objectDeleted(self):
        if self.possessed_by is not None:
            self.possessed_by.dispossessObject(self.ref())
        super(PossessableObject, self).objectDeleted()

    def nameFor(self, obj):
        """
        Return the name for normal users, or the name and ObjID for privileged
        players possessing this object.

        @param obj: The object to name.
        @type obj: L{NamedObject} or L{ObjRef}

        @return: String name of passed object as known by this object.
        @rtype: C{str}
        """
        name = super(PossessableObject, self).nameFor(obj)
        try:
            if self.player.hasPerm("see object numbers"):
                name += " (#%d)" % obj.objId
        finally:
            return name


class BaseObject(PossessableObject):
    """
    An contextual, ownable object that provides message templates, can process
    input into command execution, and provides contextual object matching.

    Ideally, all other classes should not go any lower than this class.

    @cvar private_commands: Private command classes for use by instances.
    @cvar public_commands: Commands exposed to other objects by this class.
    @cvar _commandCache: Cache of the compiled list of commands.

    @ivar owner: ObjRef() of the owner of the object (if any).
    """
    zope.interface.implements(IInputProcessor, IHasMessages, IHasCommands)

    # commands should never be set on instance, but... just in case.
    _transientVars = ['possessed_by', 'commands', 'object_settings']

    #: @type: StoredObject or ObjRef
    owner = None

    # Implement IHasCommands.
    private_commands = []
    public_commands = []
    _commandCache = {}

    # Default BaseObject locks. Will be used if object nor any intermediate
    # child class defines the lock type being searched for.
    locks = locks.LockSet('control:owner()')

    # Implements IHasMessages.
    messages = Messages()

    def __init__(self, **kwargs):
        super(BaseObject, self).__init__(**kwargs)
        self.owner = kwargs.get('owner', None)

    def getMessage(self, key, **keywords):
        """
        Return a formatted Message template. Look on self's instance first,
        then ascend the MRO looking for a class providing the requested
        message template.

        Implemented as part of L{IHasMessages}.
        """
        msg = self.messages.getMessage(key, **keywords)
        if msg is not None:
            return msg

        for cls in utils.object.ascendMro(self):
            if IHasMessages.implementedBy(cls):
                msg = cls.messages.getMessage(key, **keywords)
                return msg

        return None

    def _match(self, search, objlist, exactOnly=False, err=False):
        """
        A matching utility. Essentially a duplicate of match_objlist(), but
        instead of just pulling aliases, it pulls namesFor().
        @rtype: list
        """
        strings = dict(zip(objlist, map(lambda o: self.namesFor(o), objlist)))
        return match_stringlists(search, strings, exactOnly=exactOnly, err=err)

    def matchObject(self, search, cls=None, err=False):
        """
        A general object match for this object. Uses .namesFor() values in the
        match rather than direct aliases.

        @param search: The search string.
        @param cls: Limit potential matches to descendants of the given class
            or classes.
        @type cls: C{tuple} or C{type}
        @param err: If true, can raise search result errors.

        @rtype: list
        """
        candidate = None
        if search[0] == '#' and re.match(r"#\d+", search):
            candidate = self.game.db.getRef(int(search[1:]))
        if search.lower() == 'me':
            candidate = self.ref()

        if (candidate is not None
                and utils.object.filterByClass([candidate], cls)):
            return [candidate]

        return self._match(search,
                           utils.object.filterByClass([self.ref()], cls),
                           err=err)

    def matchObjectOfType(self, search, cls=None):
        """
        Match against all objects of a given class. Uses aliases, NOT namesFor.

        @param search: The string to match on.
        @param cls: The class whose descendants to search.
        @return: A list of matches.
        @rtype: list
        """
        cls = cls or BaseObject
        return match_objlist(search, self.game.db.descendants(cls))

    def processInput(self, raw, err=True):
        """
        Parses raw input as a command from this object and executes the first
        matching command it can find.

        The passedInput and err parameters help accommodate children overriding
        this method without having to jump through more hoops than needed.

        Implemented as part of L{IInputProcessor}.
        """
        try:
            cmd = self.findCommand(raw)
        except errors.CommandError as e:
            self.msg(e.message)
            return True
        if cmd is not None:
            cmd.execute()
            return True
        if err:
            raise errors.CommandInvalid(raw)
        return False

    def findCommand(self, raw):
        """
        Resolve the command to execute.

        @param raw: The raw command input.
        @return: An instantiated, ready-to-run command.
        @rtype: mudsling.commands.Command or None
        """
        cmd = self.preemptiveCommandMatch(raw)
        if cmd is not None:
            return cmd
        cmdstr, sep, argstr = raw.partition(' ')
        candidates = self.matchCommand(cmdstr)
        if not candidates:
            return None
        cmdMatches = []
        nameOnly = []
        for obj, cmdcls in candidates:
            cmd = cmdcls(raw, cmdstr, argstr, self.game, obj.ref(), self.ref())
            if cmd.matchSyntax(argstr):
                cmdMatches.append(cmd)
            else:
                nameOnly.append(cmd)
        if len(cmdMatches) > 1:
            raise errors.AmbiguousMatch(msg="Ambiguous Command", query=raw,
                                        matches=cmdMatches)
        elif not cmdMatches:
            if nameOnly:  # Command(s) that match name but not syntax.
                # Give each command class an opportunity to explain why. Having
                # a lot of similarly-named commands is a bad idea, so this
                # should ideally only involve one command offering some help,
                # so we raise with the first one that wants to help.
                for cmd in nameOnly:
                    msg = cmd.failedCommandMatchHelp()
                    if msg:
                        raise errors.CommandError(msg=msg)
            else:
                return self.handleUnmatchedInput(raw) or None
        else:  # Single good match.
            return cmdMatches[0]

    def matchCommand(self, cmdName):
        """
        Match a command based on name (and access).

        @param cmdName: The name of the command being search for.
        @type cmdName: C{str}

        @return: A list of tuples of (object, command class).
        @rtype: C{list}
        """
        commands = []
        for obj in self.context:
            for cmdcls in obj.commandsFor(self):
                if cmdcls.matches(cmdName) and cmdcls.checkAccess(obj, self):
                    commands.append((obj, cmdcls))
        return commands

    def commandsFor(self, actor):
        """
        Return a list of commands made available by this object to the actor.

        Returns contents of 'private_commands' if the actor is self, else it
        returns 'public_commands'. The full list of commands is built by
        ascending the MRO and adding commands from any L{IHasCommands} class.

        @param actor: The object that wishes to use a command.
        @rtype: list
        """
        if self.ref() == actor.ref():
            attr = 'private_commands'
        else:
            attr = 'public_commands'

        cls = self.__class__
        if '_commandCache' not in cls.__dict__:
            cls._commandCache = {}
        if attr in cls._commandCache:
            return cls._commandCache[attr]

        commands = []
        for objClass in utils.object.ascendMro(cls):
            if IHasCommands.implementedBy(objClass):
                commands.extend(getattr(objClass, attr))

        cls._commandCache[attr] = commands
        return commands

    def preemptiveCommandMatch(self, raw):
        """
        The object may preemptively do its own command matching (or raw data
        massaging). If this returns None, normal command matching occurs. If it
        returns a command class, that command is run. If it returns anything
        else, the command parser assumes the command was handled and takes no
        further action.

        @param raw: The raw input to handle
        @type raw: str

        @return: None, a command class, or another value.
        @rtype: type
        """
        return None

    def handleUnmatchedInput(self, raw):
        """
        Lets an object attempt to do its own parsing on command raw that was
        not handled by normal command matching.

        @param raw: The raw input to handle
        @type raw: str

        @return: A command class or None.
        @rtype: type
        """
        return None

    @property
    def context(self):
        """
        The same as self._getContext(), but with duplicates removed.
        @return:
        """
        return utils.sequence.unique(self._getContext())

    def _getContext(self):
        """
        Return a list of objects which will be checked, in order, for commands
        or object matches when parsing command arguments.

        @rtype: list
        """
        return [self.ref()]


class Object(BaseObject):
    """
    This should be the parent for most game objects. It is the object class
    that has location, and can contain other objects.

    @ivar _location: The object in which this object is located.
    @type _location: L{Object}

    @ivar _contents: The set of objects contained by this object.
    @type _contents: C{list}
    """

    #: @type: Object
    _location = None
    _contents = None

    def __init__(self, **kwargs):
        super(Object, self).__init__(**kwargs)
        self._contents = []

    @property
    def location(self):
        """
        @rtype: L{Object}
        """
        return self._location

    @property
    def contents(self):
        # Read only, enforce copy. If performance is critical, make the effort
        # to reference _contents directly (and CAREFULLY).
        return list(self._contents)

    def iterContents(self):
        for o in self._contents:
            yield o

    def objectDeleted(self):
        """
        Move self out of location and move contents out of self.
        """
        super(Object, self).objectDeleted()
        self.moveTo(None)
        this = self.ref()
        for o in list(self.contents):
            if o.location == this:
                o.moveTo(None)

    def matchObject(self, search, cls=None, err=False):
        """
        @type search: str
        @rtype: list
        """
        # Any match in parent bypasses further matching. This means, in theory,
        # that if parent matched something, something else that could match in
        # contents or location will not match. Fortunately, all we match in
        # L{BaseObject.matchObject} is object literals and self, so this sould
        # not really be an issue.
        matches = super(Object, self).matchObject(search, cls=cls)
        if not matches:
            if search.lower() == 'here' and self.location is not None:
                if utils.object.filterByClass([self.location], cls):
                    return [self.location]

            objects = list(self.contents)  # Copy is important!
            if self.hasLocation:
                objects.extend(self.location.contents)
            matches = self._match(search,
                                  utils.object.filterByClass(objects, cls),
                                  err=err)

        if err and len(matches) > 1:
            raise errors.AmbiguousMatch(matches=matches)

        return matches

    @property
    def hasLocation(self):
        """
        Returns true if the object is located somewhere valid.
        @rtype: bool
        """
        return self.location is not None and self.location.isValid(Object)

    def _getContext(self):
        """
        Add the object's location after self.
        @rtype: list
        """
        hosts = super(Object, self)._getContext()
        if self.location is not None:
            hosts.append(self.location)
        if isinstance(self.contents, list):
            hosts.extend(self.contents)
        if (self.location is not None and
                isinstance(self.location.contents, list)):
            hosts.extend(self.location.contents)

        return hosts

    def handleUnmatchedInput(self, raw):
        # Let location offer commands at this stage, too.
        cmd = super(Object, self).handleUnmatchedInput(raw)
        if not cmd:
            if self.hasLocation:
                try:
                    cmd = self.location.handleUnmatchedInputFor(self, raw)
                except AttributeError:
                    cmd = None
        return cmd

    def handleUnmatchedInputFor(self, actor, raw):
        """
        Object may ask its container for last-try command matching.
        """
        return None

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
        @type dest: Object or None

        Throws InvalidObject if this object is invalid or if the destination is
        neither None nor a valid Object instance.
        """
        me = self.ref()
        dest = dest.ref() if dest is not None else None

        if not me.isValid():
            raise errors.InvalidObject(me)

        # We allow moving to None
        if dest is not None:
            if not dest.isValid(Object):
                raise errors.InvalidObject(dest, "Destination invalid")

        previous_location = self.location
        if self.game.db.isValid(self.location, Object):
            if me in self.location._contents:
                self.location._contents.remove(me)

        self._location = dest

        if self.game.db.isValid(dest, Object):
            if me not in dest._contents:
                dest._contents.append(me)

        # Now fire event hooks on the two locations and the moved object.
        if self.game.db.isValid(previous_location, Object):
            previous_location.contentRemoved(me, dest)
        if self.game.db.isValid(dest, Object):
            dest.contentAdded(me, previous_location)

        self.objectMoved(previous_location, dest)

    def locations(self, excludeInvalid=True):
        """
        Get a list of all the nested locations where this object resides. Child
        classes should be very reluctant to override this. Unexpected return
        results may yield unexpected behaviors.

        @param excludeInvalid: If true, does not consider an invalid ObjRef to
            be a valid location, and will not include it in the list.

        @return: List of nested locations, from deepest to shallowest.
        @rtype: C{list}
        """
        locations = []
        if (isinstance(self.location, ObjRef)
                and (self.location.isValid() or not excludeInvalid)):
            locations.append(self.location)
            if self.location.isValid(Object):
                locations.extend(self.location.locations())
        return locations

    def emit(self, msg, exclude=None, location=None):
        """
        Emit a message to the object's location, optionally excluding some
        objects.

        @see: L{Object.msgContents}
        @rtype: C{list}
        """
        if location is None:
            location = self.location
        if location is None or not location.isValid(Object):
            return []
        return location.msgContents(msg, exclude=exclude)

    def emitMessage(self, key, exclude=None, location=None, **keywords):
        """
        Emit a message template to object's location.

        @param key: The key of the message to emit.
        @param keywords: The keywords for the template.

        @return: List of objects notified.
        @rtype: C{list}
        """
        keywords['this'] = self.ref()
        msg = self.getMessage(key, **keywords)
        return self.emit(msg, exclude=exclude, location=location)

    def msgContents(self, msg, exclude=None):
        """
        Send a message to the contents of this object.

        @param msg: The message to send. This can be a string, dynamic message
            list, or a dict from L{MessagedObject.getMessage}.
        @type msg: C{str} or C{dict} or C{list}

        @param exclude: List of objects to exclude from receiving the message.
        @type exclude: C{list} or C{None}

        @return: List of objects that received some form of notice.
        @rtype: C{list}
        """
        # Offers caller freedom of not having to check for None, which he might
        # get back from some message generation calls.
        if msg is None:
            return []

        # Caller may have passed objects instead of references, but we need
        # references since we're doing 'in' matching against values in
        # contents, which really, really should be references.
        exclude = [e.ref() for e in (exclude or [])
                   if isinstance(e, StoredObject) or isinstance(e, ObjRef)]

        if isinstance(msg, dict):
            # Dict keys indicate what objects receive special messages. All
            # others receive whatever's in '*'.
            _msg = lambda o: msg[o] if o in msg else msg['*']
        else:
            _msg = lambda o: msg

        receivers = []
        for o in self.contents:
            if o in exclude or not o.isValid(Object):
                continue
            o.msg(_msg(o))
            receivers.append(o)

        return receivers


class BasePlayer(BaseObject):
    """
    Base player class. Tracks account information, processes input, can possess
    objects, tracks permissions, and handles interaction with a connected
    session.

    Players are essentially 'accounts' that are connected to sessions. They can
    then possess other objects (usually Characters).

    @ivar password: The hash of the password used to login to this player.
    @ivar _email: The player's email address.
    @ivar session: The session object connected to this player.
    @ivar default_object: The object this player will possess upon connecting.
    @ivar __roles: The set of roles granted to this player.
    """

    _transientVars = ['session', 'possessing']
    session = None

    #: @type: Password
    password = None

    #: @type: str
    _email = ""

    superuser = False

    #: @type: BaseObject
    possessing = None

    #: @type: BaseObject
    default_object = None

    # Governed by ansi property
    _ansi = False

    __roles = set()

    _validNameRE = re.compile(r"[-_a-zA-Z0-9']+")

    def __init__(self, **kwargs):
        super(BasePlayer, self).__init__(**kwargs)
        self.email = kwargs.get('email', '')
        password = kwargs.get('password', None)
        if not password:
            password = utils.password.Password(utils.string.randomString(10))
        if isinstance(password, basestring):
            password = utils.password.Password(password)
        if isinstance(password, utils.password.Password):
            self.password = password

    @classmethod
    def validPlayerName(cls, name):
        """
        Validate the given player name.
        @rtype: C{bool}
        """
        return True if cls._validNameRE.match(name) else False

    @classmethod
    def create(cls, **kwargs):
        """
        Create a player.

        @raise errors.PlayerNameError: When no names given or names parameter
            is of the wrong type.
        @raise errors.InvalidPlayerName: When first name is invalid.
        @raise errors.DuplicatePlayerName: When player name is already used.
        @raise errors.InvalidEmail: When provided email is not valid.

        @return: A new player.
        @rtype: L{BasePlayer} or L{mudsling.storage.ObjRef}
        """
        names = kwargs.get('names', ())
        if not names:
            raise errors.PlayerNameError("Players require a name.")
        if not isinstance(names, tuple) and not isinstance(names, list):
            raise errors.PlayerNameError("Names must be tuple or list.")

        claimed = []
        for n in names:
            if not cls.validPlayerName(n):
                m = "%r is not a valid player name. " % n
                m += "Player names may contain "
                m += "letters, numbers, apostrophes, hyphens, and underscores."
                raise errors.InvalidPlayerName(m)
            if registry.players.findByName(n):
                claimed.append(n)
        if claimed:
            t = utils.string.english_list(claimed)
            m = "These names are already taken: %s" % t
            raise errors.DuplicatePlayerName(m)

        email = kwargs.get('email', '')
        if email and not utils.email.validEmail(email):
            m = "%r is not a valid email address." % email
            raise errors.InvalidEmail(m)
        # Default is to allow players to have duplicate emails.

        player = super(BasePlayer, cls).create(**kwargs)
        registry.players.registerPlayer(player)

        if kwargs.get('makeChar', False):
            try:
                char = cls.db.game.character_class.create(player=player.ref())
            except:
                player.delete()
                raise
            else:
                player.default_object = char

        return player

    def objectDeleted(self):
        registry.players.unregisterPlayer(self)
        super(BasePlayer, self).objectDeleted()

    def _setNames(self, name=None, aliases=None, names=None):
        """
        Players get special name handling. Specifically, they are registered
        with the player registry and cannot be duplicated.
        """
        if names is not None:
            if isinstance(names, tuple) or isinstance(names, list):
                newNames = list(names)
            else:
                raise TypeError("Names must be a list or tuple.")
        else:
            newNames = list(self._names)
            if name is not None:
                # List may be empty, so we are creative about inserting.
                newNames[0:1] = [name]
            if aliases is not None:
                newNames[1:] = aliases
        for n in newNames:
            match = registry.players.findByName(n)
            if match and match != self:
                raise errors.DuplicatePlayerName("%s already in use" % name)
        r = super(BasePlayer, self)._setNames(name, aliases, names)
        registry.players.reregisterPlayer(self)
        return r

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, val):
        self._email = val
        registry.players.reregisterPlayer(self)

    @property
    def connected(self):
        """
        @rtype: bool
        @return: Whether or not player is connected.
        """
        return self.session is not None

    @property
    def player(self):
        """
        A player is considered to be self-possessed.
        @return: BasePlayer or ObjRef
        """
        return self.ref()

    @property
    def isPosessing(self):
        """
        @rtype: bool
        @return: Whether or not player is possessing an object.
        """
        return self.possessing is not None

    def setPassword(self, password):
        self.password = utils.password.Password(password)

    def sessionAttached(self, session):
        if self.session is not None:
            # This should result in self.sessionDetached() being called
            # which will free up self.session
            self.session.disconnect("Player taken over by another connection")
        else:
            # This is a new connection as opposed to a reconnect. Attach to an
            # object.
            if self.possessing is None and self.default_object is not None:
                if (self.game.db.isValid(self.default_object, BaseObject)
                        and self.default_object.possessed_by is None):
                    self.possessObject(self.default_object)
            # TODO: Player is connecting. Should we tell someone?
            pass
        self.session = session
        session.ansi = self.ansi
        self.msg("{gConnected to player {c%s{g." % self.name)
        if self.possessing is None:
            self.msg("{rYou are not attached to any game object!")

    def sessionDetached(self, session):
        """
        Called by a session that thinks it is connected to this player upon
        disconnect.
        """
        if self.session == session:
            del self.session

    def redirectInput(self, where):
        if self.connected:
            self.session.redirectInput(where)
        else:
            raise errors.PlayerNotConnected("Cannot redirect input of a "
                                            "disconnected player.")

    def resetInput(self):
        if self.connected:
            self.session.resetInputCapture()

    def readLine(self, callback, args=()):
        """
        Captures a single line of input from the player and pass it to the
        callback.

        @param callback: The callback to receive the line of input.
        @param args: Any extra arguments to send to the callback.
        """
        def _callback(lines):
            return callback(lines[0], *args)
        self.redirectInput(utils.input.LineReader(_callback, max_lines=1))

    def readLines(self, callback, args=(), max_lines=None, end_tokens=None):
        if end_tokens is None:
            end_tokens = ('.', '@end', '@abort')
        self.redirectInput(utils.input.LineReader(callback, args=args,
                                                  max_lines=max_lines,
                                                  end_tokens=end_tokens))

    def prompt(self, callback, options, args=()):
        """
        Slight improvement on readLine which specifies a list of options. Note
        that the options are case insensitive.

        @param options: Tuple of valid values. Can be strings or compiled regex
            objects.
        @type options: tuple
        """
        if not options:
            raise ValueError("No options specified for prompt.")

        def _callback(line):
            call = False
            for o in options:
                if isinstance(o, basestring):
                    if o.lower() == line.lower():
                        call = True
                else:
                    if o.search(line):
                        call = True
            if call:
                return callback(line, *args)
            else:
                return False

        self.readLine(_callback)

    def promptCallbacks(self, options, invalidCallback=None):
        """
        Capture player input for a prompt, and call the callback corresponding
        to the option entered.

        @param options: Dict of valid responses (keys) and the callback to call
            for each option (values). Response keys can be strings or compiled
            regular expressions.
        @param invalidCallback: The callback to be called upon invalid input.
        """
        if not options:
            raise ValueError("No options specified for prompt.")

        if invalidCallback is None:
            def invalidCallback(line):
                self.msg("{rInvalid option.")
                return False

        def _do_callback(cb):
            if callable(cb):
                return cb()

        def _callback(line):
            for o in options:
                if isinstance(o, basestring):
                    if o.lower() == line.lower():
                        return _do_callback(options[o])
                elif o.search(line):
                    return _do_callback(options[o])
            return invalidCallback(line)

        self.readLine(_callback)

    def promptYesNo(self, prompt=None, yesCallback=None, noCallback=None,
                    invalidCallback=None):
        """
        Prompt user to enter 'yes' or 'no', then call the corresponding
        callback function.

        @param prompt: Text to prompt the user. Can pass False to suppress the
            default prompt.
        @param yesCallback: The callback to call upon entering 'yes'.
        @param noCallback: The callback to call upon entering 'no'.
        @param invalidCallback: The callback to be called upon invalid input.
        """
        def showPrompt():
            if prompt is not False:
                p = ''
                if isinstance(prompt, basestring):
                    p += prompt.strip() + ' '
                p += "{c[Enter '{gyes{c' or '{rno{c']"
                self.msg(p)

        if invalidCallback is None:
            def invalidCallback(line):
                self.msg("{rInvalid option.")
                showPrompt()
                return False

        showPrompt()
        self.promptCallbacks({'yes': yesCallback, 'no': noCallback},
                             invalidCallback=invalidCallback)

    def msg(self, text, flags=None):
        """
        Emit text to a player (and thereby to the session attach to the player,
        if any).

        @param text: Text to send.
        @param flags: Flags to modify how text is handled.
        @type text: str
        """
        if self.session is not None and text is not None:
            self.session.sendOutput(self._format_msg(text), flags=flags)

    def possessObject(self, obj):
        """
        Possess an object.
        @param obj: The object to possess.
        @type obj: BaseObject
        """
        if self.possessing is not None:
            self.dispossessObject(self.possessing)
        obj.possessBy(self.ref())
        if obj.possessed_by == self.ref():
            self.possessing = obj
            self.msg("{gYou have attached to {c%s{g." % self.nameFor(obj))
            self.onObjectPossessed(obj)

    def dispossessObject(self, obj):
        if self.possessing == obj:
            del self.possessing
            self.msg("{yYou have detached from {c%s{y." % self.nameFor(obj))
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
        Event hook that fires right after player has dispossessed an object.
        @param obj: The object that was previously possessed.
        @type obj: BaseObject
        """

    def processInput(self, raw, err=True):
        possessing = self.possessing is not None
        try:
            handled = super(BasePlayer, self).processInput(raw,
                                                           err=not possessing)
            if not handled and possessing:
                self.possessing.processInput(raw)
        except errors.CommandInvalid as e:
            self.msg("{r" + e.message)
        except errors.MatchError as e:
            self.msg("{y%s" % e.message)
        except NotImplementedError as e:
            m = "{y%s is not yet implemented." % (e.message or "This feature")
            self.msg(m)
        except:
            self.msg("{rAn error has occurred.")
            raise

    def hasPerm(self, perm):
        """
        Checks if this object has the permission specified. An object has a
        perm if it has a role in which that permission can be found.
        """
        if self.superuser:
            return True
        return len([role for role in self.__roles if role.hasPerm(perm)]) > 0

    def getRoles(self):
        return set(self.__roles)

    def hasRole(self, role):
        return role in self.__roles

    def addRole(self, role):
        if 'roles' not in self.__dict__:
            self.__roles = set()
        if role not in self.__roles:
            self.__roles.add(role)

    def removeRole(self, role):
        if role in self.__roles:
            self.__roles.remove(role)
        if len(self.__roles) == 0:
            del self.__roles

    def expungeRole(self, role):
        if self.hasRole(role):
            self.removeRole(role)

    @property
    def ansi(self):
        """
        @rtype: bool
        """
        return self._ansi

    @ansi.setter
    def ansi(self, val):
        if self._ansi != val:
            self._ansi = val
            if self.session is not None:
                self.session.ansi = val
            if val:
                self.msg("ANSI {gENABLED{n.")
            else:
                self.msg("ANSI DISABLED.")

    def matchObjectOfType(self, search, cls=None):
        if inspect.isclass(cls) and issubclass(cls, BasePlayer):
            if search.lower() == 'me':
                return [self.ref()]
        return super(BasePlayer, self).matchObjectOfType(search, cls=cls)

    def matchObject(self, search, cls=None, err=False):
        """
        Matching on the player will also pass the match call through to the
        object the player is possessing.

        Note that 'me' will match the possessed object if the player is
        possessing something, else it will match player object.
        """
        matches = self.possessing.matchObject(search, cls=cls, err=False)
        if not matches and self.isPosessing:
            matches = super(BasePlayer, self).matchObject(search,
                                                          cls=cls, err=err)

        if err and len(matches) > 1:
            raise errors.AmbiguousMatch(matches=matches)

        return matches


class BaseCharacter(Object):
    """
    Keep this as minimal as possible so that plugins can completely replace if
    they wish.
    """
    def __init__(self, **kwargs):
        super(BaseCharacter, self).__init__(**kwargs)
        player = kwargs.get('player', None)
        if self.game.db.isValid(player, BasePlayer):
            self.possessable_by.append(player.ref())
            if 'names' not in kwargs:
                self.setNames(player.names)
