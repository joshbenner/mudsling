

class Persistent(object):
    """
    Base class for objects persisted to the game database. This is not just
    game-world objects, but any object which gets stored and needs special
    persistence features.

    Any property whose name is prefixed with '_v_' will not be persisted. They
    will remain in place while the game is up, but any reload, restart, or
    shutdown will wipe them out. You can also specify transient attributes
    explicitly with the _transientVars class variable.

    @cvar _transientVars: Instance vars which should not persist in DB.
    @type _transientVars: list
    """

    _transientVars = ['_transientVars']

    def _getTransientVars(self):
        vars = set()
        for cls in self.__class__.__mro__:
            if '_transient' in cls.__dict__:
                try:
                    # We read from the class
                    vars = vars.union(cls._transient)
                except:
                    # TODO: Do something here?
                    pass
        return vars

    def __getstate__(self):
        transient = self._getTransientVars()
        state = self.__dict__
        for attr in state:
            if attr.startswith('_v_') or attr in transient:
                del state[attr]
        return state


class StoredObject(Persistent):
    """
    Storage class for all game-world objects. This class has no location and no
    contents. Avoid subclassing this object directly, use BaseObject or Object.
    This object cannot parse commands, cannot be connected to a player, etc.

    @ivar id: The unique object ID for this object in the game.
    @type id: int

    @ivar db: Reference to the containing database.
    @type db: Database

    @ivar name: The primary name of the object. Use name property.
    @type name: str

    @ivar aliases: A list of alternate names of the object, used for matching.
    @type aliases: list
    """

    _transientVars = ['name', 'db']

    db = None

    id = None
    _name = ""
    aliases = []

    def __init__(self):
        """
        Initialization at this level is only run when the object is first
        created. Loading from the DB does not call __init__.

        This also fires BEFORE the object has an object ID or is part of the
        database, which could suggest using objectCreated() instead.
        """
        self.aliases = []
        pass

    def name(self):
        return self._name

    def setName(self, name):
        if self._name in self.aliases:
            self.aliases.remove(self._name)
        self._name = name
        self.aliases.insert(0, name)

    name = property(name, setName)

    def objectCreated(self):
        """
        Called when the object is first created. Only called once in the life
        of the object, by Database.createObject().
        """
        pass


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
    """

    _transientVars = ['type_registry']

    max_obj_id = 0
    objects = {}
    roles = []

    type_registry = {}

    def __init__(self):
        """
        This will only run when a new game DB is initialized.
        """
        self.objects = {}
        self.roles = []
        self.type_registry = {}

    def onLoaded(self):
        """
        Called just after the database has been loaded from disk.
        """
        self.type_registry = {}
        for obj in self.objects.values():
            self._addToTypeRegistry(obj)
            obj.db = self

    def _allocateObjId(self):
        """
        Allocates a new object ID. Should only be called when a new object is
        being added to the game database.
        """
        self.max_obj_id += 1
        return self.max_obj_id

    def createObject(self, cls, name, aliases=None):
        """
        Creates a new game-world database object that will persist.
        """
        obj = cls()
        obj.name = name
        if aliases is not None:
            obj.aliases.extend(list(aliases))
        self.registerNewObject(obj)
        return obj

    def registerNewObject(self, obj):
        obj.id = self._allocateObjId()
        self.objects[obj.id] = obj
        self._addToTypeRegistry(obj)
        obj.db = self
        obj.objectCreated()

    def _addToTypeRegistry(self, obj):
        cls = obj.__class__
        if cls not in self.type_registry:
            self.type_registry[cls] = []
        if obj not in self.type_registry[cls]:
            self.type_registry[cls].append(obj)

    def isValid(self, obj):
        """
        Returns true if the passed object (or object ID) refers to a game-world
        object that the database knows about.
        """
        if isinstance(obj, int):
            return obj in self.objects
        elif isinstance(obj, StoredObject):
            return obj.id in self.objects and self.objects[obj.id] == obj
        return False

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
