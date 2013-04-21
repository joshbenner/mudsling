from collections import namedtuple
import weakref
import copy_reg
import types
import logging

from mudsling.match import match_objlist
from mudsling import errors
from mudsling import registry


# Support pickling methods.
def reduce_method(m):
    return getattr, (m.__self__, m.__func__.__name__)
copy_reg.pickle(types.MethodType, reduce_method)
del reduce_method


class ObjRef(namedtuple('ObjRef', 'id db')):
    """
    Weak references don't pickle properly. So, we provide our own proxy class
    which uses our DB-based object IDs to provide de-normalized weak reference
    powers. PersistentProxy objects can be passed around just as if they were
    the objects to which they refer, but they can out-live the objects to which
    they refer and keep the reference count low.
    """
    obj = None

    def __object(self):
        if self.obj is None:
            try:
                #noinspection PyCallByClass
                object.__setattr__(self, 'obj',
                                   weakref.ref(self.db._get_object(self.id)))
            except TypeError:
                pass
        return self.obj

    def _real_object(self):
        ref = self.__object()
        return ref() if ref is not None else None

    def __getattr__(self, name):
        return getattr(self.__object()(), name)

    def __setattr__(self, name, value):
        object.__setattr__(self.__object()(), name, value)

    def __delattr__(self, name):
        delattr(self.__object()(), name)

    def __str__(self):
        return self.__object()().__str__()

    def __repr__(self):
        r = "#%d" % self.id
        ref = self.__object()
        if ref is not None:
            r += " (%s)" % str(ref())
        else:
            r += " (invalid)"
        return r

    def __getstate__(self):
        """
        Do not pickle anything but tupley-stuff.
        """
        return False

    def __setstate__(self, state):
        pass

    def isa(self, cls):
        """
        Proxy version of isinstance.
        @rtype: bool
        """
        try:
            o = self.__object()()
            return isinstance(o, cls)
        except TypeError:
            return False

    def is_valid(self, cls=None):
        """
        Proxy version of Database.is_valid().
        """
        try:
            return self.db.is_valid(self.__object()(), cls)
        except TypeError:
            return False


class Persistent(object):
    """
    Base class for objects persisted to the game database. This is not just
    game-world objects, but any object which gets stored and needs special
    persistence features.

    Any property whose name is prefixed with '_v_' will not be persisted. They
    will remain in place while the game is up, but any reload, restart, or
    shutdown will wipe them out. You can also specify transient attributes
    explicitly with the _transient_vars class variable.

    @cvar _transient_vars: Instance vars which should not persist in DB.
    @type _transient_vars: list
    """

    _transient_vars = ['_transient_vars', 'temp', 'tmp']

    @classmethod
    def _get_transient_vars(cls):
        v = set()
        for parent in cls.__mro__:
            if '_transient_vars' in parent.__dict__:
                #noinspection PyBroadException
                try:
                    # We read from the class
                    v = v.union(parent._transient_vars)
                except:
                    # TODO: Do something here?
                    pass
        return v

    def __getstate__(self):
        transient = self._get_transient_vars()
        state = dict(self.__dict__)
        for attr in self.__dict__:
            if attr.startswith('_v_') or attr in transient:
                del state[attr]
        return state


class StoredObject(Persistent):
    """
    Storage class for all game-world objects. This class has no location and no
    contents. Avoid subclassing this object directly, use BaseObject or Object.
    This object cannot parse commands, cannot be connected to a player, etc. It
    only has the API required to interact with the database.

    @cvar db: Reference to the containing database. Set upon DB load.

    @ivar obj_id: The unique object ID for this object in the Database.
    """

    #: @type: mudsling.storage.Database
    db = None

    #: @type: int
    obj_id = 0

    def __init__(self, **kwargs):
        """
        Initialization at this level is only run when the object is first
        created. Loading from the DB does not call __init__.

        This also fires BEFORE the object has an object ID or is part of the
        database, which could suggest using objectCreated() instead.

        If you use __init__, only accept and pass **kwargs. super() can be
        harmful. StoredObject defies this rule because it will be the last to
        have its __init__ called among StoredObject descendants.

        This also means that if you use multiple-inheritance, and you specify
        a class AFTER a descendant of StoredObject, that other class will get
        NO parameters passed to its __init__.

        @see: U{https://fuhm.net/super-harmful/}

        @param db: The database into which this object is being created.
        @type db: L{Database}
        """
        super(StoredObject, self).__init__()

    def __str__(self):
        return str(self.obj_id)

    def python_class_name(self):
        return "%s.%s" % (self.__class__.__module__, self.__class__.__name__)

    def class_name(self):
        """
        @rtype: C{str}
        """
        name = registry.classes.get_class_name(self.__class__)
        return name if name is not None else self.python_class_name()

    def isa(self, cls):
        """
        Provide compatibility with ObjRef.
        @rtype: C{bool}
        """
        return isinstance(self, cls)

    def is_valid(self, cls=None):
        """
        API compatibility with ObjRef.
        @rtype: C{bool}
        """
        return self.db.is_valid(self, cls)

    def _real_object(self):
        """
        API compatibility with ObjRef.
        @rtype: StoredObject
        """
        return self

    def ref(self):
        """
        Returns an ObjRef for this object. System-level stuff should be
        sure to introduce proxies as much as possible. We want to avoid storing
        objects directly.
        """
        return ObjRef(id=self.obj_id, db=self.db)

    @property
    def game(self):
        """
        @rtype: mudsling.server.MUDSling
        """
        return self.db.game

    # TODO: Refactor this... it smells.
    def expunge_role(self, role):
        """
        API method to remove all reference to given role from this object.
        """

    @classmethod
    def create(cls, **kwargs):
        """
        Create an instance of the class and register it with the database.

        @param cls: The class to instantiate.
        @param kwargs: Any initialization arguments to pass to the class.

        @return: A reference to the new object.
        """
        if cls.db is None:
            raise Exception("Database not available to %s" % cls.__name__)
        obj = cls(**kwargs)
        cls.db.register_object(obj)
        obj.object_created()
        return obj.ref()

    def delete(self):
        """
        Canonical method for deleting an object.
        """
        self.object_deleted()
        self.db.unregister_object(self)

    def object_created(self):
        """
        Called when the object is first created. Only called once in the life
        of the object.
        """

    def object_deleted(self):
        """
        Called during object deletion, but before the object itself has been
        removed from the database. Allows the object to perform any final
        cleanup.
        """


class Database(Persistent):
    """
    A singleton of this class holds all the data that is saved to the database.

    @ivar max_obj_id: Largest game object ID number that has been allocated.
    @type max_obj_id: int

    @ivar objects: Set of all game objects.
    @type objects: dict

    @ivar roles: Game-wide roles.
    @type roles: list

    @ivar type_registry: Dictionary lookup for class instances. Rebuilt on each
        load of the database.
    @type type_registry: dict

    @ivar settings: Key/val store for arbitrary data. Can be used to store
        settings or other values that are DB-specific. Otherwise, coder should
        use the config system.
    @type settings: C{dict}

    @ivar game: Reference to the game instance.
    @type game: mudsling.core.MUDSling
    """

    _transient_vars = ['type_registry', 'game']

    initialized = False
    max_obj_id = 0
    objects = {}
    roles = []

    max_task_id = 0
    tasks = {}

    type_registry = {}

    settings = {}

    #: @type: mudsling.server.MUDSling
    game = None

    def __init__(self):
        """
        This will only run when a new game DB is initialized.
        """
        self.objects = {}
        self.roles = []
        self.tasks = {}
        self.type_registry = {}
        self.settings = {}

    def on_loaded(self, game):
        """
        Called just after the database has been loaded from disk.
        """
        self.type_registry = {}
        self.game = game
        # Add ref back to db, which also yields a trail back to game, which
        # StoredObject takes advantage of with its game property.
        StoredObject.db = self

        # Build the type registry.
        for obj in self.objects.values():
            self._add_to_type_registry(obj)

    def on_server_startup(self):
        """
        Run once per server start after everything is loaded and ready.
        """
        for task in self.tasks.itervalues():
            task.server_startup()

    def on_server_shutdown(self):
        """
        Run just prior to server shutdown.
        """
        for task in self.tasks.itervalues():
            task.server_shutdown()

    def _get_object(self, obj_id):
        try:
            return self.objects[obj_id]
        except KeyError:
            return None

    def get_ref(self, obj_id):
        return ObjRef(id=obj_id, db=self)

    def _allocate_obj_id(self):
        """
        Allocates a new object ID. Should only be called when a new object is
        being added to the game database.
        """
        self.max_obj_id += 1
        return self.max_obj_id

    def _add_to_type_registry(self, obj):
        cls = obj.__class__
        if cls not in self.type_registry:
            self.type_registry[cls] = []
        if obj not in self.type_registry[cls]:
            self.type_registry[cls].append(obj.ref())

    def register_object(self, obj):
        obj.obj_id = self._allocate_obj_id()
        self.objects[obj.obj_id] = obj
        self._add_to_type_registry(obj)

    def unregister_object(self, obj):
        """
        Deletes the passed object from the database.

        @param obj: The object to delete.
        @type obj: StoredObject or ObjRef
        """
        if not obj.is_valid():
            raise errors.InvalidObject(obj)

        obj = obj._real_object()
        try:
            del self.objects[obj.obj_id]
        except KeyError:
            logging.error("%s missing from objects dictionary!" % obj)
        try:
            self.type_registry[obj.__class__].remove(obj.ref())
        except (ValueError, KeyError):
            logging.error("%s missing from type registry!" % obj)

    def is_valid(self, obj, cls=None):
        """
        Returns true if the passed object (or object ID) refers to a game-world
        object that the database knows about.

        If class is provided, it also checks if the object is a descendant of
        the specified class.
        """
        if isinstance(obj, int):
            valid = obj in self.objects
        elif isinstance(obj, StoredObject):
            valid = (obj.obj_id in self.objects
                     and self.objects[obj.obj_id] == obj)
        elif isinstance(obj, ObjRef):
            return obj.is_valid(cls)
        else:
            return False

        if cls is not None:
            return valid and isinstance(obj, cls)

        return valid

    def descendants(self, ancestor):
        """
        Return a list of all objects with the specified class in their type
        heirarchy.

        @param ancestor: The class whose descendants to retrieve.

        @rtype: list
        """
        descendants = []
        for cls, children in self.type_registry.iteritems():
            if issubclass(cls, ancestor):
                descendants.extend(children)
        return descendants

    def children(self, parent):
        """
        Return a list of objects directly descendend from the given class.

        @param parent: The class whose children to retrieve.

        @rtype: list
        """
        if parent in self.type_registry:
            return list(self.type_registry[parent])
        return []

    def match_descendants(self, search, cls, varname="names", exactOnly=False):
        """
        Convenience method for matching the descendants of a given class.
        """
        objlist = self.descendants(cls)
        return match_objlist(search, objlist, varname, exactOnly)

    def match_children(self, search, cls, varname="names", exactOnly=False):
        """
        Convenience method for matching the children of a given class.
        """
        objlist = self.children(cls)
        return match_objlist(search, objlist, varname, exactOnly)

    def match_role(self, search):
        """
        Find a role.
        @param search: The role name to search for.
        @rtype: mudsling.perms.Role
        """
        matches = match_objlist(search, self.roles, varname="name")
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise errors.AmbiguousMatch(query=search, matches=matches)
        else:
            raise errors.FailedMatch(query=search)

    def expunge_role(self, role):
        """
        Removes role from all objects and finally the database itself.
        """
        for o in self.objects.items():
            if isinstance(o, StoredObject):
                o.expunge_role(role)
        if role in self.roles:
            self.roles.remove(role)

    def register_task(self, task):
        """
        Adds a task to the database.

        @param task: The task to register.
        @type task: mudsling.tasks.BaseTask
        """
        self.max_task_id += 1
        task.id = self.max_task_id
        task.alive = True
        self.tasks[task.id] = task

    def get_task(self, taskId):
        """
        Retrieve a task from the Database.

        @param taskId: The task ID (or perhaps the task itself).
        @return: A task object found within the Database.
        @rtype: mudsling.tasks.BaseTask
        """
        try:
            taskId = taskId if isinstance(taskId, int) else taskId.id
            task = self.tasks[taskId]
        except (AttributeError, KeyError):
            raise errors.InvalidTask("Invalid task or task ID: %r" % taskId)
        return task

    def kill_task(self, taskId):
        self.get_task(taskId).kill()

    def remove_task(self, taskId):
        task = self.get_task(taskId)
        if task.alive:
            return False
        else:
            del self.tasks[task.id]
            return True

    # Satisfies the law of demeter, and lets us change implementation later.
    def get_setting(self, name, default=None):
        return self.settings.get(name, default)

    def set_setting(self, name, value):
        self.settings[name] = value