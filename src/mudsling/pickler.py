import cPickle as pickle
import re

from mudsling import utils
import mudsling.utils.modules

_ext_id_re = re.compile(r"^(.+)~(.+)~(.+)$")
_external_types = {}


def register_external_type(cls, persistent_id, persistent_load):
    """
    Register a type to be considered 'external' along with the functions to
    return the persistent ID during pickling and instance during unpickling.

    External objects are handy if you have code-controlled instances that you
    do not wish to store in the database. This could be a strategy for reducing
    memory usage, or for enforcing code-based instance data only.

    @see U{http://docs.python.org/2/library/pickle.html#pickle-protocol}

    @param cls: The type these id/load functions apply to. Instances of this
        type will never be pickled directly, and instance persistence is the
        responsibility of the implementor.
    @param persistent_id: A function returning an ASCII persistent identifier
        when passed an object of the specified type.
    @param persistent_load: A callable returning an instance of the specified
        type when given a persistent identifier (as generated by the companion
        persistent_id function).
    """
    _external_types[cls] = (persistent_id, persistent_load)


def _persistent_id(obj):
    cls = obj.__class__
    if cls in _external_types:
        f = _external_types[cls][0]
        return "%s~%s~%s" % (cls.__module__, cls.__name__, f(obj))
    else:
        return None  # Pickle as usual.


def _persistent_load(id):
    m = _ext_id_re.match(id)
    if not m:
        raise pickle.UnpickleableError("Cannot unpickle external id: %s" % id)
    module_name, class_name, id = m.groups()
    cls = utils.modules.variable_from_module(module_name, class_name)
    if cls in _external_types:
        return _external_types[cls][1](id)
    else:
        raise pickle.UnpickleableError("No external factor for %s.%s#%s"
                                       % (module_name, class_name, id))


def dump(filepath, obj):
    with open(filepath, 'wb') as file:
        p = pickle.Pickler(file, pickle.HIGHEST_PROTOCOL)
        p.persistent_id = _persistent_id
        p.dump(obj)


def load(filepath):
    with open(filepath, 'rb') as file:
        p = pickle.Unpickler(file)
        p.persistent_load = _persistent_load
        return p.load()
