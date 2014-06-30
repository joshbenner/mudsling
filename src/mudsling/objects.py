import inspect
import re
from collections import OrderedDict

import zope.interface

from mudsling.storage import StoredObject, ObjRef
from mudsling import errors
from mudsling import locks
from mudsling import registry
from mudsling.match import match_objlist, match_stringlists
from mudsling.sessions import IInputProcessor
from mudsling.messages import IHasMessages, Messages
from mudsling.commands import IHasCommands, CommandSet

from mudsling import utils
import mudsling.utils.password
import mudsling.utils.input
import mudsling.utils.sequence
import mudsling.utils.object
import mudsling.utils.string
import mudsling.utils.internet


class LockableObject(StoredObject):
    """
    Object that can have locks associated with it.

    :cvar createLock: The lock that must be satisfied to create an instance.

    :ivar locks: The general lockset provided by the instance. Class values may
        be scanned by self.get_lock().
    """

    #: :type: locks.Lock
    create_lock = locks.none_pass

    #: :type: locks.LockSet
    locks = locks.LockSet()

    def __init__(self, **kwargs):
        super(LockableObject, self).__init__(**kwargs)
        self.locks = locks.LockSet()

    def allows(self, who, op):
        """
        Determine if who is allowed to perform op. Superusers and objects
        they possess skip the check entirely. If who has control access,
        then they are a superuser for this object.

        @param who: The object attempting the operation.
        @type who: PossessableObject or BasePlayer

        @param op: The operation (lock type) being checked.
        @type op: str

        :rtype: bool
        """
        if who.player is not None and who.player.superuser:
            return True
        return (self.get_lock(op).eval(self, who)
                or self.get_lock('control').eval(self, who))

    def get_lock(self, lockType):
        """
        Look for lock on object. If it's not there, ascend the object's MRO
        looking for a default.

        If no lock is found, then a Lock that always fails will be returned.

        @param lockType: The lock type to retrieve.
        @type lockType: str

        :rtype: mudsling.locks.Lock
        """
        if (isinstance(self.locks, locks.LockSet)
                and self.locks.has_type(lockType)):
            return self.locks.get_lock(lockType)
        for cls in utils.object.ascend_mro(self):
            if (hasattr(cls, "locks") and isinstance(cls.locks, locks.LockSet)
                    and cls.locks.has_type(lockType)):
                return cls.locks.get_lock(lockType)
        return locks.none_pass

    def set_lock(self, lock_type, lock_expr):
        """
        Set a lock for the given type on the object to the given expression.

        @param lock_type: The lock type to set.
        @param lock_expr: The lock expression to set.
        @type lock_expr: basestring or mudsling.locks.Lock
        """
        if ('locks' not in self.__dict__
                or not isinstance(self.locks, locks.LockSet)):
            self.locks = locks.LockSet()
        self.locks.set_lock(lock_type, lock_expr)


class NamedObject(LockableObject):
    """
    An object with names and can discern the names of other NamedObjects.

    :ivar _names: Tuple of all names this object is known by. First name is the
        primary name.
    """
    _names = ()
    default_names = ()

    def __init__(self, **kwargs):
        super(NamedObject, self).__init__(**kwargs)
        names = kwargs.get('names', None)
        if names:
            self.set_names(names)

    @classmethod
    def _default_names(cls):
        """Names given to instance if no names are specified."""
        if cls.default_names:
            return cls.default_names
        name = registry.classes.get_class_name(cls, class_path=False)
        if name is None:
            # Convert class CamelCase name to spaced name.
            # regex credit: http://stackoverflow.com/a/9283563
            name = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))',
                          r' \1',
                          cls.__name__)
        return name,

    def __str__(self):
        return self.name

    @property
    def name(self):
        """
        :rtype: str
        """
        return self.names[0]

    @property
    def aliases(self):
        return self.names[1:]

    @property
    def names(self):
        return self._names or self._default_names()

    @property
    def nn(self):
        """
        Return the object's name and database ID.
        :rtype: str
        """
        return "%s (#%d)" % (self.name, self.obj_id)

    def _set_names(self, name=None, aliases=None, names=None):
        """
        Low-level method for maintaining the object's names. Should only be
        called by setName or setAliases.

        @param name: The new name. If None, do not change name.
        @param aliases: The new aliases. If None, do not change aliases.
        @param names: All names in one shot. If not None, other parameters are
            ignored and only this paramter is used.
        :return: Old names tuple.
        :rtype: tuple
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

    def set_name(self, name):
        """
        Canonical method for changing the object's name. Children can override
        to attach other logic/actions to name changes.

        @param name: The new name.
        :return: The old name.
        """
        oldNames = self._set_names(name=name)
        return oldNames[0] if oldNames else None

    def set_aliases(self, aliases):
        """
        Canonical method fo changing the object's aliases. Children can
        override to attach other logic/actions to alias changes.

        @param aliases: The new aliases.
        @type aliases: list or tuple
        :return: The old aliases.
        """
        return self._set_names(aliases=aliases)[1:]

    def set_names(self, names):
        """
        Sets name and aliases is one shot, using a single list or tuple where
        the first element is the name, and the other elements are the aliases.

        @param names: The new names to use.
        :return: Old names.
        """
        oldNames = self.names
        self.set_name(names[0])
        self.set_aliases(names[1:])
        return oldNames

    def names_for(self, obj):
        """
        Returns a list of names representing the passed object as known by
        self. Default implementation is to just return all aliases.

        @param obj: The object whose "known" names to retrieve.
        @type obj: NamedObject or ObjRef
        :rtype: list
        """
        try:
            return obj.names
        except (TypeError, AttributeError):
            return []

    def name_for(self, obj):
        """
        Returns a string representation of the given object as known by self.

        @param obj: The object to name.
        @type obj: NamedObject or ObjRef

        :return: String name of passed object as known by this object.
        :rtype: str
        """
        return (self.names_for(obj) or ["UNKNOWN"])[0]

    def list_of_names(self, objs):
        """
        Return a list of names generated with self.name_for. Convenience.
        :rtype: list
        """
        return map(self.name_for, objs)


class MessagedObject(NamedObject):
    """
    Class that provides IHasMessages.
    """
    zope.interface.implements(IHasMessages)

    # Implements IHasMessages.
    messages = Messages()

    def get_message(self, key, **keywords):
        """
        Return a formatted Message template. Look on self's instance first,
        then ascend the MRO looking for a class providing the requested
        message template.

        Implemented as part of IHasMessages.
        """
        msg = self.messages.get_message(key, **keywords)
        if msg is not None:
            return msg

        for cls in utils.object.ascend_mro(self):
            if IHasMessages.implementedBy(cls):
                msg = cls.messages.get_message(key, **keywords)
                if msg is not None:
                    return msg

        return None

    def direct_message(self, key, recipients=(), **keywords):
        """
        Dispatch a templated message from this object to specific recipients.

        :param key: The key identifying the message templatme to use.
        :type key: str

        :param recipients: An iterable of message recipients.
        :type recipients: tuple or set or list or dict

        :param keywords: The keywords to pass to .get_message().
        :type keywords: dict
        """
        keywords['this'] = self.ref()
        msg = self.get_message(key, **keywords)
        if not isinstance(msg, dict):
            msg = {'*': msg}
        wild = msg.get('*', None)
        for recipient in recipients:
            message = msg[recipient] if recipient in msg else wild
            if message is not None:
                recipient.msg(message)


class PossessableObject(MessagedObject):
    """
    An object which can be possessed by a player.

    :ivar possessed_by: The BasePlayer who is currently possessing this obj.
    :ivar possessable_by: List of players who can possess this object.
    """

    _transient_vars = ['possessed_by']

    #: :type: BasePlayer
    possessed_by = None

    #: :type: list
    possessable_by = []

    def __init__(self, **kwargs):
        super(PossessableObject, self).__init__(**kwargs)
        self.possessable_by = []

    @property
    def player(self):
        """
        Return ObjRef to the player object possessing this object.
        :rtype: BasePlayer or ObjRef
        """
        if self.possessed_by is not None:
            return self.possessed_by.player
        return None

    def is_possessable_by(self, player):
        """
        Returns True if the player can possess this object.
        @param player: The player.
        :return: bool
        """
        return (player in self.possessable_by
                or player.has_perm("possess anything"))

    def become_possessed(self, player):
        """
        Become possessed by a player.
        @param player: The player possessing this object.
        @type player: BasePlayer
        """
        # TODO: Refactor this into a property?
        if self.possessed_by is not None:
            self.possessed_by.dispossess_object(self.ref())
        self.possessed_by = player
        self.on_possessed(player)

    def dispossessed(self):
        """
        Called after this object has been dispossessed by a BasePlayer.
        """
        previous = self.possessed_by
        del self.possessed_by
        if previous is not None:
            self.on_dispossessed(previous)

    def on_possessed(self, player):
        """
        Event hook called when this object has been possessed by a BasePlayer.
        @param player: BasePlayer which has possessed the object.
        @type player: BasePlayer
        """
        pass

    def on_dispossessed(self, player):
        """
        Event hook called when this object has been dispossessed by a player.
        @param player: The player that previously possessed this object.
        @type player: BasePlayer
        """
        pass

    def has_perm(self, perm):
        """
        Returns True if the player possessing this object has the passed perm.
        """
        return self.player.has_perm(perm) if self.player is not None else False

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
        @type text: str or list or tuple

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

        :rtype: str
        """
        if parts is None:
            return None
        if isinstance(parts, basestring):
            return parts
        parts = list(parts)
        for i, part in enumerate(parts):
            filter = None
            if isinstance(part, mudsling.messages.FilteredPart):
                filter = part
                part = filter.value
                parts[i] = part
            if self.db.is_valid(part, StoredObject):
                # Other children of StoredObject might be compatible with the
                # nameFor method? Shows "UNKNOWN" if not.
                parts[i] = self.name_for(part)
            if filter is not None:
                parts[i] = filter.render(parts[i])
        return ''.join(map(str, parts))

    def on_object_deleted(self):
        if self.possessed_by is not None:
            self.possessed_by.dispossess_object(self.ref())
        super(PossessableObject, self).on_object_deleted()

    def name_for(self, obj):
        """
        Return the name for normal users, or the name and ObjID for privileged
        players possessing this object.

        @param obj: The object to name.
        @type obj: NamedObject or ObjRef

        :return: String name of passed object as known by this object.
        :rtype: str
        """
        name = super(PossessableObject, self).name_for(obj)
        try:
            if self.player.has_perm("see object numbers"):
                name += " (#%d)" % obj.obj_id
        finally:
            return name


class BaseObject(PossessableObject):
    """
    An contextual, ownable object that provides message templates, can process
    input into command execution, and provides contextual object matching.

    Ideally, all other classes should not go any lower than this class.

    :cvar private_commands: Private command classes for use by instances.
    :cvar public_commands: Commands exposed to other objects by this class.
    :cvar _commandCache: Cache of the compiled list of commands.

    :ivar owner: ObjRef() of the owner of the object (if any).
    """
    zope.interface.implements(IInputProcessor, IHasCommands)

    # commands should never be set on instance, but... just in case.
    _transient_vars = ['commands', 'object_settings']

    #: :type: StoredObject or ObjRef
    owner = None

    # Implement IHasCommands.
    private_commands = []
    public_commands = []
    _command_cache = {}

    # Default BaseObject locks. Will be used if object nor any intermediate
    # child class defines the lock type being searched for.
    locks = locks.LockSet('control:owner()')

    def __init__(self, **kwargs):
        super(BaseObject, self).__init__(**kwargs)
        self.owner = kwargs.get('owner', None)

    def _match(self, search, objlist, exactOnly=False, err=False):
        """
        A matching utility. Essentially a duplicate of match_objlist(), but
        instead of just pulling aliases, it pulls namesFor().
        :rtype: list
        """
        # Use OrderedDict to preserve order of options. This is important
        # because the search string might use ordinals to avoid ambiguity.
        strings = OrderedDict(zip(objlist, map(self.names_for, objlist)))
        return match_stringlists(search, strings, exact=exactOnly, err=err)

    def match_object(self, search, cls=None, err=False):
        """
        A general object match for this object. Uses .namesFor() values in the
        match rather than direct aliases.

        @param search: The search string.
        @param cls: Limit potential matches to descendants of the given class
            or classes.
        @type cls: tuple or type
        @param err: If true, can raise search result errors.

        :rtype: list
        """
        candidate = None
        if search[0] == '#' and re.match(r"#\d+", search):
            candidate = self.game.db.get_ref(int(search[1:]))
        if search.lower() == 'me':
            candidate = self.ref()

        if (candidate is not None
                and utils.object.filter_by_class([candidate], cls)):
            return [candidate]

        return self._match(search,
                           utils.object.filter_by_class([self.ref()], cls),
                           err=err)

    def match_obj_of_type(self, search, cls=None):
        """
        Match against all objects of a given class. Uses aliases, NOT namesFor.

        @param search: The string to match on.
        @param cls: The class whose descendants to search.
        :return: A list of matches.
        :rtype: list
        """
        cls = cls or BaseObject
        return match_objlist(search, self.game.db.descendants(cls))

    def gained_input_capture(self, session):
        pass  # Here to implement IInputProcessor

    def lost_input_capture(self, session):
        pass  # Here to implement IInputProcessor

    def process_input(self, raw, err=True):
        """
        Parses raw input as a command from this object and executes the first
        matching command it can find.

        The passedInput and err parameters help accommodate children overriding
        this method without having to jump through more hoops than needed.

        Implemented as part of IInputProcessor.
        """
        try:
            cmd = self.find_command(raw)
        except errors.CommandError as e:
            self.msg(e.message)
            return True
        if cmd is not None:
            cmd.execute()
            return True
        if err:
            raise errors.CommandInvalid(raw)
        return False

    def find_command(self, raw):
        """
        Resolve the command to execute.

        :param raw: The raw command input.
        :return: An instantiated, ready-to-run command.
        :rtype: mudsling.commands.Command or None
        """
        cmd = self.preemptive_command_match(raw)
        if cmd is not None:
            return cmd
        cmdstr, sep, argstr = raw.partition(' ')
        candidates = self.match_command(cmdstr)
        if not candidates:
            return self.handle_unmatched_input(raw) or None
        cmd_matches = []
        name_only = []
        for obj, cmdcls in candidates:
            cmd = cmdcls(raw, cmdstr, argstr, self.game, obj.ref(), self.ref())
            if cmd.match_syntax(argstr):
                cmd_matches.append(cmd)
            else:
                name_only.append(cmd)
        if len(cmd_matches) > 1:
            raise errors.AmbiguousMatch(msg="Ambiguous Command", query=raw,
                                        matches=cmd_matches)
        elif not cmd_matches:
            if name_only:  # Command(s) that match name but not syntax.
                # Give each command class an opportunity to explain why. Having
                # a lot of similarly-named commands is a bad idea, so this
                # should ideally only involve one command offering some help,
                # so we raise with the first one that wants to help.
                help_shown = []
                msg = []
                for cmd in name_only:
                    cls = cmd.__class__
                    if cls not in help_shown:
                        msg.append(cmd.failed_command_match_help())
                        help_shown.append(cls)
                if msg:
                    raise errors.CommandError(msg='\n'.join(msg))
        else:  # Single good match.
            return cmd_matches[0]

    def match_command(self, cmd_name):
        """
        Match a command based on name (and access).

        @param cmd_name: The name of the command being search for.
        @type cmd_name: str

        :return: A list of tuples of (object, command class).
        :rtype: list
        """
        commands = []
        for obj in self.context:
            matches = obj.commands_for(self).match(cmd_name, obj, self)
            commands.extend(zip([obj] * len(matches), matches))
        return commands

    def commands_for(self, actor):
        """
        Return a list of commands made available by this object to the actor.

        Returns contents of 'private_commands' if the actor is self, else it
        returns 'public_commands'. The full list of commands is built by
        ascending the MRO and adding commands from any IHasCommands class.

        @param actor: The object that wishes to use a command.
        :rtype: CommandSet
        """
        if self.ref() == actor.ref():
            attr = 'private_commands'
        else:
            attr = 'public_commands'

        cls = self.__class__
        if '_command_cache' not in cls.__dict__:
            cls._command_cache = {}
        if attr in cls._command_cache:
            commands = cls._command_cache[attr]
        else:
            commands = CommandSet()
            for obj_class in utils.object.descend_mro(cls):
                if IHasCommands.implementedBy(obj_class):
                    commands.add_commands(getattr(obj_class, attr))
            cls._command_cache[attr] = commands

        return commands

    def preemptive_command_match(self, raw):
        """
        The object may preemptively do its own command matching (or raw data
        massaging). If this returns None, normal command matching occurs. If it
        returns a command class, that command is run. If it returns anything
        else, the command parser assumes the command was handled and takes no
        further action.

        @param raw: The raw input to handle
        @type raw: str

        :return: None, a command class, or another value.
        :rtype: type
        """
        return None

    def handle_unmatched_input(self, raw):
        """
        Lets an object attempt to do its own parsing on command raw that was
        not handled by normal command matching.

        @param raw: The raw input to handle
        @type raw: str

        :return: A command *instance* or None.
        :rtype: mudsling.commands.Command
        """
        return None

    @property
    def context(self):
        """
        The same as self._get_context(), but with duplicates removed.
        :return:
        """
        return utils.sequence.unique(self._get_context())

    def _get_context(self):
        """
        Return a list of objects which will be checked, in order, for commands
        or object matches when parsing command arguments.

        :rtype: list
        """
        return [self.ref()]

    def on_server_startup(self):
        super(BaseObject, self).on_server_startup()


class Object(BaseObject):
    """
    This should be the parent for most game objects. It is the object class
    that has location, and can contain other objects.

    :ivar _location: The object in which this object is located.
    :type _location: Object

    :ivar _contents: The set of objects contained by this object.
    :type _contents: list of Object
    """
    _location = None
    _contents = None

    def __init__(self, **kwargs):
        super(Object, self).__init__(**kwargs)
        #: :type: list of Object
        self._contents = []

    def delete(self):
        self.move_to(None)
        return super(Object, self).delete()

    @property
    def location(self):
        """
        :rtype: Object
        """
        return self._location

    @property
    def contents(self):
        """
        :rtype: list of Object
        """
        # Read only, enforce copy. If performance is critical, make the effort
        # to reference _contents directly (and CAREFULLY).
        return list(self._contents)

    def contents_name(self, viewer=None):
        """
        The string to display for this object when seen in a list of contents.

        :param viewer: An optional viewer object.
        :type viewer: BaseObject

        :return: The name to show while in the contents list of its container.
        :rtype: str
        """
        return self.name if viewer is None else viewer.name_for(self)

    def can_touch(self, obj):
        obj = obj.ref()
        if self.has_location and obj in self.location.contents:
            return True
        return obj in self.contents

    def iterContents(self):
        for o in self._contents:
            yield o

    def on_object_deleted(self):
        """
        Move self out of location and move contents out of self.
        """
        super(Object, self).on_object_deleted()
        self.move_to(None)
        this = self.ref()
        for o in list(self.contents):
            if o.location == this:
                o.move_to(None)

    def match_context(self, search, cls=None, err=False):
        """
        Match an object, but only match objects in this object's context. This
        excludes matching of any objects not in this object's contents or
        location.

        :param search: The search text.
        :type search: str

        :param cls: A class to limit potential matches.
        :type cls: type

        :param err: Whether or not to raise match errors.
        :type err: bool

        :return: List of matches.
        :rtype: list of Object
        """
        index = dict((o, o.names + ('#%d' % o.obj_id,))
                     for o in utils.object.filter_by_class(self.context, cls))
        if self.location in index:
            index[self.location] += ('here',)
        if self in index:
            index[self] += ('me',)
        return match_stringlists(search, index, exact=False, err=err)

    def match_object(self, search, cls=None, err=False):
        """
        :type search: str
        :rtype: list
        """
        # Any match in parent bypasses further matching. This means, in theory,
        # that if parent matched something, something else that could match in
        # contents or location will not match. Fortunately, all we match in
        # BaseObject.match_object is object literals and self, so this sould
        # not really be an issue.
        matches = super(Object, self).match_object(search, cls=cls)
        if not matches:
            if search.lower() == 'here' and self.location is not None:
                if utils.object.filter_by_class([self.location], cls):
                    return [self.location]

            objects = list(self.contents)  # Copy is important!
            if self.has_location:
                objects.extend(self.location.contents)
            matches = self._match(search,
                                  utils.object.filter_by_class(objects, cls),
                                  err=err)

        if err and len(matches) > 1:
            raise errors.AmbiguousMatch(matches=matches)

        return matches

    def match_contents(self, search, cls=None, err=False):
        candidate = None
        if search[0] == '#' and re.match(r"#\d+", search):
            candidate = self.game.db.get_ref(int(search[1:]))

        if (candidate is not None and candidate in self.contents
                and utils.object.filter_by_class([candidate], cls)):
            return [candidate]

        candidates = utils.object.filter_by_class(list(self.contents), cls)
        return self._match(search, candidates, err=err)

    @property
    def has_location(self):
        """
        Returns true if the object is located somewhere valid.
        :rtype: bool
        """
        return self.location is not None and self.location.is_valid(Object)

    def _get_context(self):
        """
        Add the object's location after self.
        :rtype: list
        """
        hosts = super(Object, self)._get_context()
        if self.location is not None:
            hosts.append(self.location)
        if isinstance(self.contents, list):
            hosts.extend(self.contents)
        if (self.location is not None and
                isinstance(self.location.contents, list)):
            hosts.extend(self.location.contents)

        return hosts

    def handle_unmatched_input(self, raw):
        # Let location offer commands at this stage, too.
        cmd = super(Object, self).handle_unmatched_input(raw)
        if not cmd:
            if self.has_location:
                try:
                    cmd = self.location.handle_unmatched_input_for(self, raw)
                except AttributeError:
                    cmd = None
        return cmd

    def handle_unmatched_input_for(self, actor, raw):
        """
        Object may ask its container for last-try command matching.
        :returns: Command *instance*.
        :rtype: mudsling.commands.Command
        """
        return None

    def before_content_removed(self, what, destination, by=None, via=None):
        """
        Called before an object is removed from the contents of this object.
        Objects that wish to prevent the move can raise a MoveError here.

        :param what: The object that will be moved.
        :param destination: Where the object will be moved.

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement will occur.
        :type via: BaseObject or basestring
        """
        pass

    def before_content_added(self, what, previous_location, by=None, via=None):
        """
        Called before and object is added to the contents of this object.
        Objects that wish to prevent th emove can raise a MoveError here.

        :param what: The object that will be moved.
        :param previous_location: Where the object was previously.

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement will occur.
        :type via: BaseObject or basestring
        """
        pass

    def after_content_removed(self, what, destination, by=None, via=None):
        """
        Called if an object was removed from this object.

        :param what: The object that moved
        :type what: Object

        :param destination: Where the object went.
        :type destination: Object

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement occurred.
        :type via: BaseObject or basestring
        """
        pass

    def after_content_added(self, what, previous_location, by=None, via=None):
        """
        Called when an object is added to this object's contents.

        :param what: The object that was moved.
        :type what: Object

        :param previous_location: Where the moved object used to be.
        :type previous_location: Object

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement occurred.
        :type via: BaseObject or basestring
        """
        pass

    def before_object_moved(self, moving_from, moving_to, by=None, via=None):
        """
        Called before this object is moved from one location to another.
        Objects can prevent movement by raising a MoveError here.

        :param moving_from: The previous (likely current) location.
        :type moving_from: Object

        :param moving_to: The destination (likely next) location.
        :type moving_to: Object

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement would occur.
        :type via: BaseObject or basestring
        """
        pass

    def after_object_moved(self, moved_from, moved_to, by=None, via=None):
        """
        Called when this object was moved.

        :param moved_from: Where this used to be.
        :type moved_from: Object

        :param moved_to: Where this is now.
        :type moved_to: Object

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement occurred.
        :type via: BaseObject or basestring
        """
        pass

    def move_to(self, dest, by=None, via=None):
        """
        Move the object to a new location. Updates contents on source and
        destination, and fires corresponding hooks on all involved.

        :param dest: Where to move the object. Can be None or Object.
        :type dest: Object or None

        :param by: The object responsible for the movement. Often a character.
        :type by: BaseObject

        :param via: The object or other method by which movement occurs.
        :type via: BaseObject or basestring

        Throws InvalidObject if this object is invalid or if the destination is
        neither None nor a valid Object instance.

        May throw a MoveError, in which case the move did not occurr and the
        error should contain information explaining why.
        """
        this = self.ref()
        #: :type: Object
        dest = dest.ref() if dest is not None else None

        if not this.is_valid():
            raise errors.InvalidObject(this)

        # We allow moving to None
        if dest is not None:
            if not dest.is_valid(Object):
                raise errors.InvalidObject(dest, "Destination invalid")

        source = self.location
        source_valid = self.game.db.is_valid(source, Object)
        dest_valid = self.game.db.is_valid(dest, Object)

        # Check for recursive moves.
        if dest_valid and (this == dest or this in dest.locations()):
            raise errors.RecursiveMove(this, source, dest)

        # Notify objects about the move about to happen, allowing them to raise
        # exceptions if they need to halt the move.
        self.before_object_moved(source, dest, by, via)
        if source_valid:
            source.before_content_removed(this, dest, by, via)
        if dest_valid:
            dest.before_content_added(this, source, by, via)

        if source_valid:
            if this in self.location._contents:
                self.location._contents.remove(this)

        self._location = dest

        if dest_valid:
            if this not in dest._contents:
                dest._contents.append(this)

        # Now fire event hooks on the two locations and the moved object.
        if source_valid:
            source.after_content_removed(this, dest, by, via)
        if dest_valid:
            dest.after_content_added(this, source, by, via)

        self.after_object_moved(source, dest, by, via)

    def locations(self, exclude_invalid=True):
        """
        Get a list of all the nested locations where this object resides. Child
        classes should be very reluctant to override this. Unexpected return
        results may yield unexpected behaviors.

        @param exclude_invalid: If true, does not consider an invalid ObjRef to
            be a valid location, and will not include it in the list.

        :return: List of nested locations, from deepest to shallowest.
        :rtype: list of Object
        """
        locations = []
        if (isinstance(self.location, ObjRef)
                and (self.location.is_valid() or not exclude_invalid)):
            locations.append(self.location)
            if self.location.is_valid(Object):
                locations.extend(self.location.locations())
        return locations

    def emit(self, msg, exclude=None, location=None):
        """
        Emit a message to the object's location, optionally excluding some
        objects.

        See: :method:`Object.msg_contents`

        :rtype: list
        """
        if location is None:
            location = self.location
        if location is None or not location.is_valid(Object):
            return []
        return location.msg_contents(msg, exclude=exclude)

    def emit_message(self, key, exclude=None, location=None, **keywords):
        """
        Emit a message template to object's location.

        @param key: The key of the message to emit.
        @param keywords: The keywords for the template.

        :return: List of objects notified.
        :rtype: list
        """
        keywords['this'] = self.ref()
        location = location or self.location
        msg = self.get_message(key, **keywords)
        return self.emit(msg, exclude=exclude, location=location)

    def msg_contents(self, msg, exclude=None):
        """
        Send a message to the contents of this object.

        @param msg: The message to send. This can be a string, dynamic message
            list, or a dict from MessagedObject.get_message.
        @type msg: str or dict or list

        @param exclude: List of objects to exclude from receiving the message.
        @type exclude: list or None

        :return: List of objects that received some form of notice.
        :rtype: list
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
            if o in exclude or not o.is_valid(Object):
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

    :ivar password: The hash of the password used to login to this player.
    :ivar _email: The player's email address.
    :ivar session: The session object connected to this player.
    :ivar default_object: The object this player will possess upon connecting.
    :ivar __roles: The set of roles granted to this player.
    """

    _transient_vars = ['session', 'possessing']
    session = None

    #: :type: Password
    password = None

    #: :type: str
    _email = ""

    superuser = False

    #: :type: BaseObject
    possessing = None

    #: :type: BaseObject
    default_object = None

    # Governed by ansi property
    _ansi = False
    _xterm256 = False

    __roles = set()

    _valid_name_re = re.compile(r"[-_a-zA-Z0-9']+")

    def __init__(self, **kwargs):
        super(BasePlayer, self).__init__(**kwargs)
        self.email = kwargs.get('email', '')
        password = kwargs.get('password', None)
        if not password:
            password = utils.password.Password(utils.string.random_string(10))
        if isinstance(password, basestring):
            password = utils.password.Password(password)
        if isinstance(password, utils.password.Password):
            self.password = password

    @classmethod
    def valid_player_name(cls, name):
        """
        Validate the given player name.
        :rtype: bool
        """
        return True if cls._valid_name_re.match(name) else False

    @classmethod
    def create(cls, **kwargs):
        """
        Create a player.

        @raise errors.PlayerNameError: When no names given or names parameter
            is of the wrong type.
        @raise errors.InvalidPlayerName: When first name is invalid.
        @raise errors.DuplicatePlayerName: When player name is already used.
        @raise errors.InvalidEmail: When provided email is not valid.

        :return: A new player.
        :rtype: BasePlayer or mudsling.storage.ObjRef
        """
        names = kwargs.get('names', ())
        if not names:
            raise errors.PlayerNameError("Players require a name.")
        if not isinstance(names, tuple) and not isinstance(names, list):
            raise errors.PlayerNameError("Names must be tuple or list.")

        claimed = []
        for n in names:
            if not cls.valid_player_name(n):
                m = "%r is not a valid player name. " % n
                m += "Player names may contain "
                m += "letters, numbers, apostrophes, hyphens, and underscores."
                raise errors.InvalidPlayerName(m)
            if registry.players.find_by_name(n):
                claimed.append(n)
        if claimed:
            t = utils.string.english_list(claimed)
            m = "These names are already taken: %s" % t
            raise errors.DuplicatePlayerName(m)

        email = kwargs.get('email', '')
        if email and not utils.internet.valid_email(email):
            m = "%r is not a valid email address." % email
            raise errors.InvalidEmail(m)
        # Default is to allow players to have duplicate emails.

        player = super(BasePlayer, cls).create(**kwargs)
        registry.players.register_player(player)

        if kwargs.get('makeChar', False):
            try:
                char = cls.db.game.character_class.create(player=player.ref())
            except:
                player.delete()
                raise
            else:
                player.default_object = char
                room = cls.db.get_setting('player start')
                if cls.db.is_valid(room, Object):
                    char.move_to(room)

        return player

    def on_object_deleted(self):
        registry.players.unregister_player(self)
        super(BasePlayer, self).on_object_deleted()

    def _set_names(self, name=None, aliases=None, names=None):
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
            match = registry.players.find_by_name(n)
            if match and match != self:
                raise errors.DuplicatePlayerName("%s already in use" % name)
        r = super(BasePlayer, self)._set_names(name, aliases, names)
        registry.players.reregister_player(self)
        return r

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, val):
        self._email = val
        registry.players.reregister_player(self)

    @property
    def connected(self):
        """
        :rtype: bool
        :return: Whether or not player is connected.
        """
        return self.session is not None

    @property
    def player(self):
        """
        A player is considered to be self-possessed.
        :return: BasePlayer or ObjRef
        """
        return self.ref()

    @property
    def is_possessing(self):
        """
        :rtype: bool
        :return: Whether or not player is possessing an object.
        """
        return self.possessing is not None

    def set_password(self, password):
        self.password = utils.password.Password(password)

    def authenticate(self, password, session=None):
        """
        Attempt to authenticate with the given password. Session is optional
        but can also be used to authenticate (IP/host auth, etc).
        """
        if isinstance(self.password, utils.password.Password):
            return self.password.matches_password(password)
        raise TypeError("Password not set.")

    def session_attached(self, session):
        if self.session is not None:
            # This should result in self.session_detached() being called
            # which will free up self.session
            self.session.disconnect("Player taken over by another connection")
        else:
            # This is a new connection as opposed to a reconnect. Attach to an
            # object.
            if self.possessing is None and self.default_object is not None:
                if (self.game.db.is_valid(self.default_object, BaseObject)
                        and self.default_object.possessed_by is None):
                    self.possess_object(self.default_object)
            # TODO: Player is connecting. Should we tell someone?
            pass
        self.session = session
        session.ansi = self.ansi
        session.xterm256 = self.xterm256
        self.msg("{gConnected to player {c%s{g." % self.name)
        if self.possessing is None:
            self.msg("{rYou are not attached to any game object!")

    def session_detached(self, session):
        """
        Called by a session that thinks it is connected to this player upon
        disconnect.
        """
        if self.session == session:
            del self.session

    def redirect_input(self, where):
        if self.connected:
            self.session.redirect_input(where)
        else:
            raise errors.PlayerNotConnected("Cannot redirect input of a "
                                            "disconnected player.")

    def reset_input(self):
        if self.connected:
            self.session.reset_input_capture()

    def read_line(self, callback, args=()):
        """
        Captures a single line of input from the player and pass it to the
        callback.

        @param callback: The callback to receive the line of input.
        @param args: Any extra arguments to send to the callback.
        """
        def _callback(lines):
            return callback(lines[0], *args)
        self.redirect_input(utils.input.LineReader(_callback, max_lines=1))

    def read_lines(self, callback, args=(), max_lines=None, end_tokens=None):
        if end_tokens is None:
            end_tokens = ('.', '@end', '@abort')
        self.redirect_input(utils.input.LineReader(callback, args=args,
                                                   max_lines=max_lines,
                                                   end_tokens=end_tokens))

    def prompt(self, callback, options, args=()):
        """
        Slight improvement on read_line which specifies a list of options. Note
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

        self.read_line(_callback)

    def prompt_callbacks(self, options, invalidCallback=None):
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

        self.read_line(_callback)

    def prompt_yes_no(self, prompt=None, yes_callback=None, no_callback=None,
                      invalid_callback=None):
        """
        Prompt user to enter 'yes' or 'no', then call the corresponding
        callback function.

        @param prompt: Text to prompt the user. Can pass False to suppress the
            default prompt.
        @param yes_callback: The callback to call upon entering 'yes'.
        @param no_callback: The callback to call upon entering 'no'.
        @param invalid_callback: The callback to be called upon invalid input.
        """
        def __show_prompt():
            if prompt is not False:
                p = ''
                if isinstance(prompt, basestring):
                    p += prompt.strip() + ' '
                p += "{c[Enter '{gyes{c' or '{rno{c']"
                self.msg(p)

        if invalid_callback is None:
            def invalid_callback(line):
                self.msg("{rInvalid option.")
                __show_prompt()
                return False

        __show_prompt()
        self.prompt_callbacks({'yes': yes_callback, 'no': no_callback},
                              invalidCallback=invalid_callback)

    def msg(self, text, flags=None):
        """
        Emit text to a player (and thereby to the session attach to the player,
        if any).

        @param text: Text to send.
        @param flags: Flags to modify how text is handled.
        @type text: str
        """
        if self.session is not None and text is not None:
            self.session.send_output(self._format_msg(text), flags=flags)

    def possess_object(self, obj):
        """
        Possess an object.
        @param obj: The object to possess.
        @type obj: BaseObject
        """
        if self.possessing is not None:
            self.dispossess_object(self.possessing)
        obj.become_possessed(self.ref())
        if obj.possessed_by == self.ref():
            self.possessing = obj
            self.msg("{gYou have attached to {c%s{g." % self.name_for(obj))
            self.on_object_possessed(obj)

    def dispossess_object(self, obj):
        if self.possessing == obj:
            del self.possessing
            self.msg("{yYou have detached from {c%s{y." % self.name_for(obj))
            obj.dispossessed()
            self.on_object_dispossessed(obj)

    def on_object_possessed(self, obj):
        """
        Event hook that fires right after BasePlayer has possessed an object.
        @param obj: The object that is now possessed by the player.
        @type obj: BaseObject
        """

    def on_object_dispossessed(self, obj):
        """
        Event hook that fires right after player has dispossessed an object.
        @param obj: The object that was previously possessed.
        @type obj: BaseObject
        """

    def process_input(self, raw, err=True):
        possessing = self.possessing is not None
        try:
            handled = super(BasePlayer, self).process_input(raw,
                                                            err=not possessing)
            if not handled and possessing:
                self.possessing.process_input(raw)
        except errors.CommandInvalid as e:
            self.msg("{r" + e.message)
        except errors.SilentError:
            # Silently do nothing.
            pass
        except (errors.MatchError, errors.ParseError, errors.MoveError) as e:
            self.msg("{y%s" % e.message)
        except NotImplementedError as e:
            m = "{y%s is not yet implemented." % (e.message or "This feature")
            self.msg(m)
        except:
            self.msg("{rAn error has occurred.")
            raise

    def has_perm(self, perm):
        """
        Checks if this object has the permission specified. An object has a
        perm if it has a role in which that permission can be found.
        """
        if self.superuser:
            return True
        return len([role for role in self.__roles if role.has_perm(perm)]) > 0

    def get_roles(self):
        return set(self.__roles)

    def has_role(self, role):
        return role in self.__roles

    def add_role(self, role):
        if 'roles' not in self.__dict__:
            self.__roles = set()
        if role not in self.__roles:
            self.__roles.add(role)

    def remove_role(self, role):
        if role in self.__roles:
            self.__roles.remove(role)
        if len(self.__roles) == 0:
            del self.__roles

    def expunge_role(self, role):
        if self.has_role(role):
            self.remove_role(role)

    @property
    def ansi(self):
        """
        :rtype: bool
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

    @property
    def xterm256(self):
        """:rtype: bool"""
        return self._xterm256

    @xterm256.setter
    def xterm256(self, val):
        if self._xterm256 != val:
            if val:
                self.ansi = val
            self._xterm256 = val
            if self.session is not None:
                self.session.xterm256 = val
            if val:
                self.msg('256 color support {gENABLED{n.')
            else:
                self.msg('256 color support {rDISABLED{n.')

    def match_obj_of_type(self, search, cls=None):
        if inspect.isclass(cls) and issubclass(cls, BasePlayer):
            if search.lower() == 'me':
                return [self.ref()]
        return super(BasePlayer, self).match_obj_of_type(search, cls=cls)

    def match_object(self, search, cls=None, err=False):
        """
        Matching on the player will also pass the match call through to the
        object the player is possessing.

        Note that 'me' will match the possessed object if the player is
        possessing something, else it will match player object.
        """
        matches = self.possessing.match_object(search, cls=cls, err=False)
        if not matches and self.is_possessing:
            matches = super(BasePlayer, self).match_object(search,
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
        if self.game.db.is_valid(player, BasePlayer):
            self.possessable_by.append(player.ref())
            if 'names' not in kwargs:
                self.set_names(player.names)
