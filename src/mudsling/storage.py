import copy_reg
import types
import logging
import os
import sys
import time

from twisted.internet.task import LoopingCall

from mudsling.match import match_objlist
from mudsling import errors
from mudsling import registry
from mudsling import pickler


# Support pickling methods.
def reduce_method(m):
    return getattr, (m.__self__, m.__func__.__name__)
copy_reg.pickle(types.MethodType, reduce_method)
del reduce_method


class PersistentSlots(object):
    """
    Parent which supports pickling classes that make use of slots, and explicit
    exclusion of some slots from pickling. Slot-based cousin of L{Persistent}.

    To keep things simple,

    @see U{http://code.activestate.com/recipes/578433}
    """
    __slots__ = ()

    _transient_vars = []

    @classmethod
    def _all_slots(cls):
        slots = []
        for ancestor in cls.__mro__:
            if '__slots__' in ancestor.__dict__:
                slots.extend(ancestor.__slots__)
        return slots

    def __getstate__(self):
        return dict(
            (slot, getattr(self, slot))
            for slot in self._all_slots()
            if slot not in self._transient_vars and hasattr(self, slot)
        )

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)


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


class ObjRef(PersistentSlots):
    """
    Weak references don't pickle properly. So, we provide our own proxy class
    which uses our DB-based object IDs to provide de-normalized weak reference
    powers. ObjRef objects can be passed around just as if they were the
    objects to which they refer, but they can out-live the objects to which
    they refer and keep the reference count low.
    """
    __slots__ = ('_id',)
    db = None  # This dependency is injected immediately after the db loads.

    @property
    def id(self):
        return self._id

    def __new__(cls, id=0, db=None):
        """Compatibility with old namedtuple implementation"""
        obj = super(ObjRef, cls).__new__(cls)
        obj._id = id
        return obj

    def __setstate__(self, state):
        """Compatibility with old namedtuple implementation"""
        if isinstance(state, bool) and not state:
            return
        return super(ObjRef, self).__setstate__(state)

    def _real_object(self):
        return self.db._get_object(self._id)

    def __getattr__(self, name):
        return getattr(self._real_object(), name)

    def __setattr__(self, name, value):
        if name == '_id':
            obj = self
        else:
            obj = self._real_object()
        object.__setattr__(obj, name, value)

    def __delattr__(self, name):
        delattr(self._real_object(), name)

    def __str__(self):
        return str(self._real_object())

    def __repr__(self):
        r = "#%d" % self._id
        ref = self._real_object()
        if ref is not None:
            r += " (%s)" % str(ref)
        else:
            r += " (invalid)"
        return r

    def __hash__(self):
        return self._id

    def __cmp__(self, other):
        if other is None:
            return -1
        if isinstance(other, (ObjRef, StoredObject)):
            return self._id.__cmp__(other.obj_id)
        raise TypeError("ObjRefs may only be compared with other ObjRefs or "
                        "StoredObjects")

    def isa(self, cls):
        """
        Proxy version of isinstance.
        @rtype: bool
        """
        try:
            o = self._real_object()
            return isinstance(o, cls)
        except TypeError:
            return False

    def is_valid(self, cls=None):
        """
        Proxy version of Database.is_valid().
        """
        try:
            return self.db.is_valid(self._real_object(), cls)
        except TypeError:
            return False


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

    def __hash__(self):
        return self.obj_id

    def __eq__(self, other):
        if isinstance(other, (ObjRef, StoredObject)):
            return other.obj_id == self.obj_id
        return False

    def __cmp__(self, other):
        if isinstance(other, (ObjRef, StoredObject)):
            return self.obj_id.__cmp__(other.obj_id)
        raise TypeError("Cannot compare game objects with other types.")

    def change_class(self, newclass, **kw):
        return self.db.change_class(self, newclass, **kw)

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
        return ObjRef(id=self.obj_id)

    @property
    def game(self):
        """
        :rtype: mudsling.core.MUDSling
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
        obj.on_object_created()
        return obj.ref()

    def delete(self):
        """
        Canonical method for deleting an object.
        """
        self.on_object_deleted()
        self.db.unregister_object(self)

    def on_object_created(self):
        """
        Called when the object is first created. Only called once in the life
        of the object.
        """

    def on_object_deleted(self):
        """
        Called during object deletion, but before the object itself has been
        removed from the database. Allows the object to perform any final
        cleanup.
        """

    def on_server_startup(self):
        """
        Called after the server has started.
        """

    def server_shutdown(self):
        """
        Called just before the server shuts down.
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

    _transient_vars = ['type_registry', 'game', 'filepath']

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

    filepath = ''

    @classmethod
    def load(cls, filepath, game):
        if os.path.exists(filepath):
            logging.info("Loading database from %s" % filepath)
            start = time.clock()
            db = cls._load(filepath)
            duration = time.clock() - start
            logging.info("  -> loaded %d objects" % len(db.objects))
            logging.info("  -> loaded in %.3f seconds" % duration)
        else:
            logging.info("Initializing new database at %s" % filepath)
            db = cls(filepath)
        db.filepath = filepath
        ObjRef.db = db
        logging.info('Running post-load database hooks...')
        start = time.clock()
        db.on_loaded(game)
        duration = time.clock() - start
        logging.info('  -> hooks ran in %.3f seconds' % duration)
        return db

    @classmethod
    def _load(cls, filepath):
        return pickler.load(filepath)

    def __init__(self, filepath):
        """
        This will only run when a new game DB is initialized.
        """
        self.filepath = filepath
        self.objects = {}
        self.roles = []
        self.tasks = {}
        self.type_registry = {}
        self.settings = {}

    def on_loaded(self, game):
        """
        Called just after the database has been loaded from disk.
        """
        self.game = game
        # Add ref back to db, which also yields a trail back to game, which
        # StoredObject takes advantage of with its game property.
        StoredObject.db = self
        self.rebuild_type_registry()

    def rebuild_type_registry(self):
        self.type_registry = {}

        import gc
        toggle_gc = gc.isenabled()

        # Build the type registry.
        if toggle_gc:
            gc.disable()
        for obj in self.objects.itervalues():
            self._add_to_type_registry(obj)
        if toggle_gc:
            gc.collect()
            gc.enable()

    def on_server_startup(self):
        """
        Run once per server start after everything is loaded and ready.
        """
        for task in self.tasks.itervalues():
            task.server_startup()
        for obj in self.objects.itervalues():
            obj.on_server_startup()

    def on_server_shutdown(self):
        """
        Run just prior to server shutdown.
        """
        for obj in self.objects.itervalues():
            obj.server_shutdown()
        for task in self.tasks.itervalues():
            task.server_shutdown()

    def save(self, filepath=None):
        filepath = filepath or self.filepath
        logging.info("Dumping database to %s..." % filepath)
        self.filepath = filepath

        def dump():
            start = time.clock()
            pickler.dump(filepath, self)
            dur = time.clock() - start
            logging.info('  -> completed in %.3f seconds' % dur)

        if 'fork' in dir(os):
            pid = os.fork()
            if pid == 0:  # Child process writing the DB to disk.
                # noinspection PyBroadException
                try:
                    dump()
                except Exception:
                    logging.error("Cannot save database", exc_info=1)
                    os._exit(1)
                else:
                    os._exit(0)
            else:
                logging.info('  -> dumping in PID %d' % pid)

                def check_status():
                    child_pid, status = os.waitpid(pid, os.WNOHANG)
                    if child_pid != 0:
                        raise Exception()

                def checkpoint_done(f):
                    pass

                looper = LoopingCall(check_status)
                d = looper.start(0.1)
                d.addErrback(checkpoint_done)
        else:
            logging.info('  -> NON-FORKED DUMP, MAY SLOW DOWN SERVER')
            dump()

    def _get_object(self, obj_id):
        try:
            return self.objects[obj_id]
        except KeyError:
            return None

    def get_ref(self, obj_id):
        return ObjRef(id=obj_id)

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
            self.type_registry[cls] = set()
        if obj.obj_id not in self.type_registry[cls]:
            self.type_registry[cls].add(obj.obj_id)

    def change_class(self, obj, newclass, **kw):
        """
        Change the class of the object.

        This process will actually instantiate a new object of ``newclass`` and
        copy the state from ``obj`` to the new object. Finally, the new object
        will replace ``obj`` in the database.

        :param obj: The object whose class to change.
        :param newclass: The new parent class of the object.
        :param kw: The keyword arguments to pass the the new object init.
        """
        obj = obj._real_object()
        newobj = newclass(**kw)
        newobj.__dict__.update(obj.__dict__)
        self.unregister_object(obj)
        self.register_object(newobj, force_id=obj.obj_id)
        newobj.on_object_created()
        return newobj.ref()

    def register_object(self, obj, force_id=None):
        obj.obj_id = force_id or self._allocate_obj_id()
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
            self.type_registry[obj.__class__].remove(obj.obj_id)
        except (ValueError, KeyError):
            logging.error("%s missing from type registry!" % obj)
        try:
            del self.objects[obj.obj_id]
        except KeyError:
            logging.error("%s missing from objects dictionary!" % obj)

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
        return map(ObjRef, descendants)

    def children(self, parent):
        """
        Return a list of objects directly descendend from the given class.

        @param parent: The class whose children to retrieve.

        @rtype: list
        """
        if parent in self.type_registry:
            return map(ObjRef, self.type_registry[parent])
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

    def new_task_id(self):
        self.max_task_id += 1
        return self.max_task_id

    # Satisfies the law of demeter, and lets us change implementation later.
    def get_setting(self, name, default=None):
        return self.settings.get(name, default)

    def set_setting(self, name, value):
        self.settings[name] = value
