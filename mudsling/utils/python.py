"""
Misc utilities for manipulating Python, data structures, etc.
"""
import collections


def is_mutable(val):
    immutable = (isinstance(val, basestring) or isinstance(val, int)
                 or isinstance(val, long) or isinstance(val, bool)
                 or isinstance(val, float) or isinstance(val, tuple))
    return not immutable


def objTreeReplace(root, search, replace, remove=False, seen=None):
    """
    Walks all objects/values in an object tree, given the root node, and
    replaces the given value with the specified replacement. If the 'remove'
    paremeter is True, then when the value is found in a collection, it will
    be removed if possible.

    @param root: The root object whose tree to walk deeply.
    @param search: The value to be replaced
    @param replace: The value to replace the old value.
    @param remove: If True, remove the search value from collections.
    """
    seen = seen or set()
    if isinstance(root, collections.Hashable):
        try:
            if root in seen:
                return
            seen.add(root)
        except TypeError:
            pass
    if isinstance(root, list):
        toremove = []
        for i, val in enumerate(root):
            if val == search:
                if remove:
                    toremove.append(i)
                else:
                    root[i] = replace
            elif is_mutable(val):
                objTreeReplace(val, search, replace, remove=remove, seen=seen)
        for i in toremove:
            del root[i]
    elif isinstance(root, dict):
        toremove = []
        for key, val in root.iteritems():
            if val == search:
                if remove:
                    toremove.append(key)
                else:
                    root[key] = replace
            elif is_mutable(val):
                objTreeReplace(val, search, replace, remove=remove, seen=seen)
        for i in toremove:
            del root[i]
    elif isinstance(root, set):
        toremove = []
        toadd = []
        for val in root:
            if val == search:
                toremove.append(val)
                if not remove:
                    toadd.append(replace)
            elif is_mutable(val):
                objTreeReplace(val, search, replace, remove=remove, seen=seen)
        for i in toremove:
            root.remove(i)
        for i in toadd:
            root.add(i)
    else:
        try:
            objTreeReplace(root.__dict__, search, replace, remove=remove,
                           seen=seen)
        except AttributeError:
            pass
