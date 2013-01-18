

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
        for cls in type.mro(self.__class__):
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
        state = []
        for attr in self.__dict__:
            if attr.startswith('_v_') or attr in transient:
                continue
            state.append(attr)
        return state


class GameObject(Persistent):
    """
    Storage class for all game-world objects. This class has no location and no
    contents. Avoid subclassing this object directly, use Object or
    PhysicalObject. This object cannot parse commands, cannot be connected to a
    player, etc.

    @ivar id: The unique object ID for this object in the game.
    @type id: int

    @ivar name: The primary name of the object. Use name property.
    @type name: str

    @ivar aliases: A set of alternate names of the object, used for matching.
    @type aliases: set
    """

    _transientVars = ['name']

    id = None
    _name = ""
    aliases = set()

    def __init__(self):
        """
        Initialization at this level is only run when the object is first
        created. Loading from the DB does not call __init__.

        This also fires BEFORE the object has an object ID or is part of the
        database, which could suggest using objectCreated() instead.
        """
        pass

    def name(self):
        return self._name

    def setName(self, name):
        self.aliases.remove(self._name)
        self._name = name
        self.aliases.add(name)

    name = property(name, setName)

    def objectCreated(self):
        """
        Called when the object is first created. Only called once in the life
        of the object, by Database.createObject().
        """
        pass


class Database(object):
    """
    A singleton of this class holds all the data that is saved to the database.

    @ivar max_obj_id: Largest game object ID number that has been allocated.
    @type max_obj_id: int

    @ivar objects: Set of all game objects.
    @type objects: dict
    """

    max_obj_id = 0
    objects = {}

    def __init__(self):
        """
        This will only run when a new game DB is initialized.
        """
        self.objects = {}

    def _allocateObjId(self):
        """
        Allocates a new object ID. Should only be called when a new object is
        being added to the game database.
        """
        self.max_obj_id += 1
        return self.max_obj_id

    def createObject(self, cls):
        """
        Creates a new game-world database object that will persist.
        """
        obj = cls()
        obj.id = self._allocateObjId()
        self.objects[obj.id] = obj
        obj.objectCreated()
        return obj

    def isValid(self, obj):
        """
        Returns true if the passed object (or object ID) refers to a game-world
        object that the database knows about.
        """
        if isinstance(obj, int):
            return obj in self.objects
        elif isinstance(obj, GameObject):
            return obj.id in self.objects and self.objects[obj.id] == obj
        return False
