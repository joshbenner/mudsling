

class Database(object):
    """
    A singleton of this class holds all the data that is saved to the database.

    @ivar objects: Set of all game objects.
    @type objects: set
    """

    objects = set()

    def __init__(self):
        """
        This will only run when a new game DB is initialized.
        """
        self.objects = set()


class Persistent(object):
    """
    Base class for objects persisted to the game database.

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
                    """TODO: Do something here?"""
        return vars

    def __getstate__(self):
        transient = self._getTransientVars()
        state = []
        for attr in self.__dict__:
            if attr.startswith('_v_') or attr in transient:
                continue
            state.append(attr)
        return state
