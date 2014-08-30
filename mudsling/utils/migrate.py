"""
Migration utilities.
"""


def forward_class(newClass):
    """
    Creates a dynamic class whose sole function is to forward to another class.
    This is useful when renaming or changing the location of a class.

    If we are renaming class 'foo.Bar' to 'foo.Baz', then we might put this in
    the foo.py file:
        >>> from mudsling.utils.migrate import forward_class
        >>> Bar = forward_class(Baz)

    @param newClass: The class to forward to.
    @return: A dynamically-created class which will forward instantiations of
        the old class to the new class transparently.
    """
    class _class(object):
        def __new__(cls, *args, **kwargs):
            return newClass.__new__(newClass, *args, **kwargs)

        def __setstate__(self, state):
            self.__dict__.update(state)
            self.__class__ = newClass

    return _class
