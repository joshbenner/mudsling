import inspect

from mudsling.storage import StoredObject, ObjRef
from mudsling import errors
from mudsling.utils.password import Password
from mudsling.utils.input import LineReader
from mudsling.match import match_objlist, match_stringlists
from mudsling.sessions import InputProcessor


class ObjSetting(object):
    """
    Describes an object setting available in-game.
    """

    name = ''
    type = None
    attr = None
    parser = None
    validator = None
    default = None

    def __init__(self, name, type=str, attr=None, default=None, parser=None,
                 validator=None):
        self.name = name
        self.type = type
        self.attr = attr
        self.parser = parser
        self.validator = validator
        self.default = default

    @staticmethod
    def parseStringList(string):
        return map(str.strip, string.split(','))

    @staticmethod
    def parseStringListNoneEmpty(string):
        return filter(lambda x: x, ObjSetting.parseStringList(string))

    def setValue(self, obj, input):
        """
        Sets the value for the setting this instance describes on the provided
        object to the provided value.

        @returns: True if set action succeeds.
        @rtype: bool
        """
        if callable(self.parser):
            try:
                value = self.parser(obj, self, input)
            except errors.ObjSettingError:
                raise
            except Exception as e:
                msg = "Error parsing input: %s" % e.message
                raise errors.ObjSettingError(obj, self.name, msg)
        else:
            value = input

        if callable(self.validator):
            try:
                valid = self.validator(obj, self, value)
            except Exception as e:
                raise errors.ObjSettingError(obj, self.name, e.message)
            if not valid:
                raise errors.InvalidSettingValue(obj, self.name, value)

        # Type validation for StoredObject is a little different since we use
        # ObjRef in most cases instead of direct references.
        if issubclass(self.type, StoredObject):
            if not issubclass(value, ObjRef) or not value.isValid(self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)
        else:
            if not isinstance(value, self.type):
                raise errors.InvalidSettingValue(obj, self.name, value)

        # If we get this far, then value is valid.
        attr = self.attr
        if attr is None:  # Store in unbound_settings
            if "unbound_settings" in obj.__dict__:
                if obj.unbound_settings is None:
                    obj.unbound_settings = {}
                obj.unbound_settings[self.name] = value
                return True
            else:
                return False
        else:
            if hasattr(obj, attr):
                try:
                    setattr(obj, attr, value)
                    return True
                except Exception as e:
                    raise errors.ObjSettingError(obj, self.name, e.message)
            else:
                return False

    def getValue(self, obj):
        attr = self.attr
        if attr is None:
            if "unbound_settings" in obj.__dict__:
                if attr in obj.unbound_settings:
                    return obj.unbound_settings[attr]
        else:
            if hasattr(obj, attr):
                return getattr(obj, attr)
        return self.default


class BaseObject(StoredObject, InputProcessor):
    """
    The base class for all other objects. You may subclass this if you need an
    object without location or contents. You should use this instead of
    directly subclassing StoredObject.

    @cvar commands: Commands provided by this class. Classes, not instances.

    @ivar possessed_by: The BasePlayer who is currently possessing this object.
    @ivar possessable_by: List of players who can possess this object.
    @ivar __roles: The set of roles granted to this object. For most objects,
        this variable will always be empty. Characters and especially players,
        however, may have occasion to be granted roles.
    @ivar unbound_settings: Dict to store values for any object settings which
        do not have an associated attribute.
    """

    # commands should never be set on instance, but... just in case.
    _transientVars = ['possessed_by', 'commands', 'object_settings']

    #: @type: list
    commands = []

    #: @type: BasePlayer
    possessed_by = None

    #: @type: list
    possessable_by = []

    __roles = set()

    object_settings = {
        # Examples. These attributes will be managed with purposed commands.
        #'name': ObjSetting('name', str, 'name'),
        #'aliases': ObjSetting('aliases', list, 'aliases',
        #                      ObjSetting.parseStringListNoneEmpty)
    }
    _objSettings_cache = None

    #: @type: dict
    unbound_settings = None

    def pythonClassName(self):
        return "%s.%s" % (self.__class__.__module__, self.__class__.__name__)

    def className(self):
        name = self.game.getClassName(self.__class__)
        return name if name is not None else self.pythonClassName()

    def objectDeleted(self):
        super(BaseObject, self).objectDeleted()
        if self.possessed_by is not None:
            self.possessed_by.dispossessObject(self.ref())

    @classmethod
    def objSettings(cls):
        """
        Returns a dict of ObjSetting instances that apply to this class. The
        ObjSettings come from this class and all ancestor classes that specify
        a list of ObjSettings.

        @return: Dict of ObjSetting instances describing the settings for obj.
        @rtype: dict of str:ObjSetting
        """
        if cls._objSettings_cache is not None:
            return cls._objSettings_cache
        mro = list(cls.__mro__)
        mro.reverse()
        settings = {}
        for c in mro:
            if issubclass(c, BaseObject) and 'object_settings' in c.__dict__:
                for name, spec in c.object_settings.iteritems():
                    settings[name] = spec
        cls._objSettings_cache = settings
        return settings

    def setObjSetting(self, name, input):
        """
        Set the value of an object setting.
        @param name: The object setting to manipulate.
        @param input: The raw user input representing the value to store.
        """
        settings = self.objSettings()
        if name not in settings:
            raise errors.SettingNotFound(self, name)
        return settings[name].setValue(self, input)

    def getObjSetting(self, name):
        settings = self.objSettings()
        if name not in settings:
            raise errors.SettingNotFound(self, name)
        return settings[name].getValue(self)

    def namesFor(self, obj):
        """
        Returns a list of names representing the passed object as known by
        self. Default implementation is to just return all aliases.

        @param obj: The object whose "known" names to retrieve.
        @type obj: StoredObject or ObjRef
        @rtype: list
        """
        try:
            return obj.aliases
        except (TypeError, AttributeError):
            return []

    def nameFor(self, obj):
        """
        Returns a string representation of the given object as known by self.
        The default implementation is to return the name for normal users, or
        the name and ObjID for admin users.

        @param obj: The object to name.
        @type obj: StoredObject or ObjRef

        @return: String name of passed object as known by this object.
        @rtype: str
        """
        name = (self.namesFor(obj) or ["UNKNOWN"])[0]
        try:
            if self.player.hasPerm("see object numbers"):
                name += " (#%d)" % obj.id
        finally:
            return name

    def expungeRole(self, role):
        if self.hasRole(role):
            self.removeRole(role)

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

    def msg(self, text, flags=None):
        """
        Primary method of emitting text to an object (and any players/sessions
        which are attached to it).

        @param text: The text to send to the object.
        @param flags: Flags to modify how text is handled.
        @type text: str or list
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
        if isinstance(parts, basestring):
            return parts
        for i, part in enumerate(parts):
            if isinstance(part, ObjRef) or isinstance(part, StoredObject):
                parts[i] = self.nameFor(part)
        return ''.join(map(str, parts))

    def _match(self, search, objlist, exactOnly=False, err=False):
        """
        A matching utility. Essentially a duplicate of match_objlist(), but
        instead of just pulling aliases, it pulls namesFor().
        @rtype: list
        """
        strings = dict(zip(objlist, map(lambda o: self.namesFor(o), objlist)))
        return match_stringlists(search, strings, exactOnly=exactOnly, err=err)

    def matchObject(self, search, err=False):
        """
        A general object match for this object. Uses .namesFor() values in the
        match rather than direct aliases.

        @param search: The search string.
        @param err: If true, can raise search result errors.

        @rtype: list
        """
        # TODO: Literal object matching
        if search.lower() == 'me':
            return [self.ref()]
        return self._match(search, [self.ref()], err=err)

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
            raise errors.CommandInvalid(input)
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
        for obj in self.getContext():
            for cmdcls in obj.commandsFor(self):
                if cmdcls.checkAccess(self) and cmdcls.matches(cmdstr):
                    cmd = cmdcls(raw, cmdstr, argstr, self.game, obj.ref(),
                                 self.ref())
                    if cmd.matchSyntax(argstr):
                        return cmd
                    elif not cmd.require_syntax_match:
                        raise errors.CommandError(cmd.syntaxHelp())
        cmd = self.handleUnmatchedInput(raw)
        if cmd is not None:
            return cmd
        return None

    def commandsFor(self, actor):
        """
        Return a list of commands made available by this object to the actor.
        @param actor: The object that wishes to use a command.
        @rtype: list
        """
        return self.commands

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

    def getContext(self):
        """
        Return a list of objects which will be checked, in order, for commands
        or object matches when parsing command arguments.

        @rtype: list
        """
        return [self]

    def hasPerm(self, perm):
        """
        Checks if this object has the permission specified. An object has a
        perm if it has a role in which that permission can be found.
        """
        return len([role for role in self.roles if role.hasPerm(perm)]) > 0

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


class Object(BaseObject):
    """
    This should be the parent for most game objects. It is the object class
    that has location, and can contain other objects.

    @ivar location: The object in which this object is located.
    @type location: Object

    @ivar contents: The set of objects contained by this object.
    @type contents: list
    """

    #: @type: Object
    location = None
    contents = None

    def __init__(self):
        super(Object, self).__init__()
        self.contents = []

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

    def matchObject(self, search, err=False):
        """
        @type search: str
        @rtype: list
        """
        matches = super(Object, self).matchObject(search)
        if not matches:
            if search.lower() == 'here' and self.location is not None:
                return [self.location]

            matches = self._match(search, self.contents, err=False)
            if not matches:
                matches = self._match(search, self.location.contents, err=err)

        if err and len(matches) > 1:
            raise errors.AmbiguousMatch(matches=matches)

        return matches

    def getContext(self):
        """
        Add the object's location after self.
        @rtype: list
        """
        hosts = super(Object, self).getContext()
        if self.location is not None:
            hosts.append(self.location)
        if isinstance(self.contents, list):
            hosts.extend(self.contents)
        if (self.location is not None and
                isinstance(self.location.contents, list)):
            hosts.extend(self.location.contents)

        return hosts

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
            self.location.contents.remove(me)

        self.location = dest

        if self.game.db.isValid(dest, Object):
            dest.contents.append(me)

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
        @rtype: list
        """
        locations = []
        if (isinstance(self.location, ObjRef)
                and (self.location.isValid() or not excludeInvalid)):
            locations.append(self.location)
            if self.location.isValid(Object):
                locations.extend(self.location.locations())
        return locations


class BasePlayer(BaseObject):
    """
    Base player class.

    Players are essentially 'accounts' that are connected to sessions. They can
    then possess other objects (usually Characters).

    @ivar password: The hash of the password used to login to this player.
    @ivar email: The player's email address.
    @ivar session: The session object connected to this player.
    @ivar default_object: The object this player will possess upon connecting.
    """

    _transientVars = ['session', 'possessing']
    session = None

    #: @type: Password
    password = None

    #: @type: str
    email = ""

    superuser = False

    #: @type: BaseObject
    possessing = None

    #: @type: BaseObject
    default_object = None

    # Governed by ansi property
    _ansi = False

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
        self.password = Password(password)

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
        self.redirectInput(LineReader(_callback, max_lines=1))

    def readLines(self, callback, args=(), max_lines=None, end_tokens=None):
        if end_tokens is None:
            end_tokens = ('.', '@end', '@abort')
        self.redirectInput(LineReader(callback, args=args, max_lines=max_lines,
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
        if self.session is not None:
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
            raise
        except:
            self.msg("{rAn error has occurred.")
            raise

    def hasPerm(self, perm):
        if self.superuser:
            return True
        return super(BasePlayer, self).hasPerm(perm)

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

    def matchObject(self, search, err=False):
        """
        Matching on the player will also pass the match call through to the
        object the player is possessing.

        Note that 'me' will match the possessed object if the player is
        possessing something, else it will match player object.
        """
        matches = self.possessing.matchObject(search, err=False)
        if not matches and self.isPosessing:
            matches = super(BasePlayer, self).matchObject(search, err=err)

        if err and len(matches) > 1:
            raise errors.AmbiguousMatch(matches=matches)

        return matches


class BaseCharacter(Object):
    """
    Keep this as minimal as possible so that plugins can completely replace if
    they wish.
    """
    pass
