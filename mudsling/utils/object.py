

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
