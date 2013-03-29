import inspect


def filterByClass(objects, cls):
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
                    if o.isValid(c):
                        valid = True
                        break
                except AttributeError:
                    continue
            if valid:
                filtered.append(o)
        return filtered
    else:
        return list(objects)


def ascendMro(cls):
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


def descendMro(cls):
    mro = ascendMro(cls)
    mro.reverse()
    return mro
