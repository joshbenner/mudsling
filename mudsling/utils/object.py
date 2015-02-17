import inspect
from functools import wraps


# noinspection PyUnresolvedReferences,PyMethodOverriding
class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class AttributeAlias(object):
    def __init__(self, original, obj=None):
        self.original = original
        self.obj = obj

    def __get__(self, obj, objtype=None):
        # Works on instances AND classes.
        obj = self.obj or obj
        if obj is not None:
            return getattr(obj, self.original)
        else:
            return getattr(objtype, self.original)

    def __set__(self, obj, value):
        # Only works for instances!
        obj = self.obj or obj
        return setattr(obj, self.original, value)

    def __delete__(self, obj):
        # Only works for instances!
        obj = self.obj or obj
        delattr(obj, self.original)


class memoize(object):
    def __init__(self, cache=None, num_args=None):
        """
        Memoize the output of a function, optionally specifying an external
        cache and a limited number of arguments to consider when caching.

        :param cache: A dict-like object for storing the cache.
        :param num_args: The number of arguments to consider when caching.

        .. note:: ``num_args`` is not compatible with keyword arguments.
        """
        self.cache = cache if cache is not None else {}
        self.num_args = num_args

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if self.num_args is not None:
                cache_key = str(args[:self.num_args])
            else:
                cache_key = repr(args) + repr(kwargs)
            if cache_key in self.cache:
                return self.cache[cache_key]
            result = f(*args, **kwargs)
            self.cache[cache_key] = result
            return result
        return wrapper


class memoize_property(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, cache=None):
        super(memoize_property, self).__init__(fget, fset, fdel, doc)
        self.cache = cache if cache is not None else {}

    def __get__(self, obj, type=None):
        if obj in self.cache:
            return self.cache[obj]
        result = super(memoize_property, self).__get__(obj, type)
        self.cache[obj] = result
        return result


def filter_by_class(objects, cls):
    """Filter a list of objects to only descendants of a class or classes.

    :param objects: Objects to filter.
    :type: list

    :param cls: Class(es) that objects must be descendant from. If None is
        passed, then no filtering is done.
    :type: type or tuple or None

    :return: List of filtered objects.
    :rtype: list
    """
    if cls is not None:
        filtered = []
        classes = cls if isinstance(cls, tuple) else (cls,)
        for o in objects:
            valid = False
            for c in classes:
                try:
                    if o.is_valid(c):
                        valid = True
                        break
                except AttributeError:
                    continue
            if valid:
                filtered.append(o)
        return filtered
    else:
        return list(objects)


def ascend_mro(cls):
    """Return an iterable to ascend the MRO of the provided object, whether an
    instance or a class.

    :param cls: Instance or class whose MRO to ascend.

    :rtype: list
    """
    if not inspect.isclass(cls):
        cls = cls.__class__
    mro = type.mro(cls)
    return mro


def descend_mro(cls):
    mro = ascend_mro(cls)
    mro.reverse()
    return mro


def dict_inherit(obj, member, key):
    """Ascend the object or class's MRO, looking at a member containing a dict.
    Each dict is check for the provided key, until the key is found and its
    corresponding value is returned.

    :param obj: The object whose MRO to search for the dictionary key.
    :type obj: type or object

    :param member: The member containing the dictionary.
    :type member: str

    :param key: The dictionary key to look for.

    :return: The value for the given key from the first object in the MRO whose
        member dictionary possesses the indicated key.

    :raises KeyError: if the key is not found in the member anywhere in MRO.
    """
    if inspect.isclass(obj):
        mro = obj.__mro__
    else:
        mro = [obj]
        mro.extend(ascend_mro(obj))
    for o in mro:
        try:
            d = getattr(o, member)
        except AttributeError:
            continue
        if isinstance(d, dict) and key in d:
            return d[key]
    raise KeyError


def has_callable(obj, member):
    """
    Return true if object has a callable member with the specified name.

    :rtype: bool
    """
    return hasattr(obj, member) and callable(getattr(obj, member))


def check_attr(obj, member, default=None):
    """
    Check that an attribute is set on the provided object.
    """
    cls = type(obj)
    if member in cls.__dict__ and isinstance(getattr(cls, member), property):
        # We don't do anything with properties.
        return getattr(obj, member)
    try:
        if member in obj.__dict__:
            return getattr(obj, member)
    except AttributeError:
        # Slots?
        try:
            return getattr(obj, member)
        except AttributeError:
            pass
    setattr(obj, member, default)
    return getattr(obj, member)


def inheritors(cls):
    """
    Get a list of all classes that inherit from the given new-style class.
    :rtype: set
    """
    subclasses = set()
    work = [cls]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses
