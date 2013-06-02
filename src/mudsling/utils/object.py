import inspect


# noinspection PyUnresolvedReferences,PyMethodOverriding
class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


## {{{ http://code.activestate.com/recipes/578433/ (r1)
class SlotPickleMixin(object):
    def __getstate__(self):
        return dict(
            (slot, getattr(self, slot))
            for slot in self.__slots__
            if hasattr(self, slot)
        )

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)
## end of http://code.activestate.com/recipes/578433/ }}}


def filter_by_class(objects, cls):
    """
    Filter a list of objects to only descendants of a class or classes.

    @param objects: Objects to filter.
    @type: C{list}

    @param cls: Class(es) that objects must be descendant from. If None is
        passed, then no filtering is done.
    @type: C{type} or C{None}

    @return: List of filtered objects.
    @rtype: C{list}
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
    """
    Return an iterable to ascend the MRO of the provided object, whether an
    instance or a class.

    @param cls: Instance or class whose MRO to ascend.

    @rtype: C{list}
    """
    if not inspect.isclass(cls):
        cls = cls.__class__
    mro = type.mro(cls)
    return mro


def descend_mro(cls):
    mro = ascend_mro(cls)
    mro.reverse()
    return mro
