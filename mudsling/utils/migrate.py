"""
Migration utilities.
"""

module_name_map = {}
class_name_map = {}


def forward_class(new_class):
    """
    Creates a dynamic class whose sole function is to forward to another class.
    This is useful when renaming or changing the location of a class.

    If we are renaming class 'foo.Bar' to 'foo.Baz', then we might put this in
    the foo.py file:
        >>> from mudsling.utils.migrate import forward_class
        >>> Bar = forward_class(Baz)

    :param new_class: The class to forward to.
    :type new_class: type or str

    :return: A dynamically-created class which will forward instantiations of
        the old class to the new class transparently.
    """
    class _class(object):
        def __new__(cls, *args, **kwargs):
            if isinstance(new_class, str):
                from mudsling.utils.modules import class_from_path
                new_cls = class_from_path(new_class)
            else:
                new_cls = new_class
            return new_cls.__new__(new_cls, *args, **kwargs)

        def __setstate__(self, state):
            self.__dict__.update(state)
            self.__class__ = new_class

    return _class


def rename_module(oldname, newname):
    module_name_map[oldname] = newname


def rename_class(oldname, newname):
    class_name_map[oldname] = newname
