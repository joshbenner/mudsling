"""
Modular composition of classes and instances.

Decorators are classes that extend the functionality of other classes or even
instances.

Decorators can be easily added to and removed from classes and instances. They
are useful when host objects offer decorators opportunities to extend
their functionality, such as invoking hooks on decorators or collecting
decorator data (ie: decorator-provided commands).

Decorators can also transparently provide new attributes and methods to classes
and instances they decorate. They are essentially modular plugins for classes
and instances.

Components are instances that can be added to other instances to add modular
functionality. Components are more similar to traditional composition, where
the composed object contains the components, but use a consistent API for
adding, removing, and hooking into the functionality of the host objects they
compose.
"""
import inspect
import types
from collections import OrderedDict


def hook(func):
    func.is_hook = True
    return func


def is_hook(func):
    return ((inspect.ismethod(func) or inspect.isfunction(func))
            and getattr(func, 'is_hook', False))


class Decorator(object):
    """
    Decorators are classes that provide attributes and methods to be accessible
    by instances they are associated with (at class or instance level).

    Decorators are not supposed to be instanced, because their attributes are
    transparently proxied to be accessible by instances that have access to
    them.

    Example: If you learn math, that becomes a decorator of your person. You do
    not possess an instance of math, but rather math knowledge is now a part of
    your mind, its processes are available to you, and it stores information in
    you, such as which concepts you understand, a running tab when counting,
    and so on.

    You may write a Decorator largely like you would write a parent class, but
    there are some notable differences:
    * _init_decorator is called during Decorated initialization.
    * Special attribute methods like __getattr__ are never called.
    * Decorators are not in the instance MRO, and are not searched by super().
    * Decorator methods may not use super(). If decorators use inheritance, you
        must use composed parent calls instead: parentClass.same_method(*args)
    """
    @classmethod
    def _decorator_attr(cls, name, owner):
        if name.startswith('__'):  # Hide magic attributes.
            raise AttributeError
        val = getattr(cls, name)
        if is_hook(val):  # Hide hooks.
            raise AttributeError
        if inspect.ismethod(val):
            bind_to = val.im_self or owner
            val = types.MethodType(val.im_func, bind_to)
        return val

    @classmethod
    def implements_hook(cls, hook):
        func = getattr(cls, hook, None)
        if func is not None and getattr(func, 'is_hook', False):
            return True
        return False

    def _init_decorator(self, *a, **kw):
        # Stop init here. Decorators should be last parents.
        pass


class Decorated(object):
    """
    An object with decorators.

    Decorators are collected from the instance, and all classes in the MRO of
    the instance.
    """
    _decorators = []

    @classmethod
    def _init_class_decorators(cls):
        if '_decorators' not in cls.__dict__:
            cls._decorators = []

    @classmethod
    def add_class_decorator(cls, decorator):
        cls._init_class_decorators()
        cls._decorators.append(decorator)

    @classmethod
    def remove_class_decorator(cls, decorator):
        cls._init_class_decorators()
        if decorator in cls._decorators:
            cls._decorators.remove(decorator)

    @classmethod
    def get_class_decorators(cls, parent=Decorator):
        decs = []
        for c in cls.__mro__:
            if issubclass(c, Decorated) and '_decorators' in c.__dict__:
                decs.extend(f for f in c._decorators if issubclass(f, parent)
                            and not f in decs)
        return decs

    def __init__(self, *args, **kwargs):
        self._decorators = []
        for dec in self._decorators:
            if '__init__' in dec.__dict__:
                dec.__init__.im_func(self, *args, **kwargs)
        super(Decorated, self).__init__(*args, **kwargs)

    @property
    def decorators(self):
        return self.get_decorators()

    def add_decorator(self, decorator):
        if decorator in self._decorators:
            return
        self._decorators.append(decorator)

    def remove_decorator(self, decorator):
        if decorator in self._decorators:
            self._decorators.remove(decorator)

    def has_decorator(self, decorator):
        return decorator in self.decorators

    def __getattr__(self, name):
        for decorator in (f for f in self.decorators if hasattr(f, name)):
            return decorator._decorator_attr(name, self)
        clsname = self.__class__.__name__
        msg = "'%s' object has no attribute '%s'" % (clsname, name)
        raise AttributeError(msg)

    def get_decorators(self, parent=Decorator):
        """
        Get a list of decorators associated with this instance.

        @param parent: An optional parent class by which to filter decorators.

        @rtype: C{list}
        """
        decorators = filter(lambda f: issubclass(f, parent),
                            getattr(self, '_decorators', []))
        decorators.extend(self.__class__.get_class_decorators(parent=parent))
        return decorators

    def decorator_hook_implementations(self, hook, parent=Decorator):
        impl = OrderedDict()
        for decorator in self.get_decorators(parent=parent):
            if decorator.implements_hook(hook):
                func = getattr(decorator, hook)
                bind = func.im_self or self
                impl[decorator] = types.MethodType(func.im_func, bind)
        return impl

    def invoke_decorator_hook(self, hook, *a, **kw):
        parent = kw.get('parent', Decorator)
        impl = self.decorator_hook_implementations(hook, parent=parent)
        return OrderedDict([(f, h(*a, **kw)) for f, h in impl.iteritems()])


class Component(object):
    """
    A modular piece of functionality which can be hosted by a parent instance.

    Components are supposed to be instantiated and are largely their own
    objects that just happen to enhance or complement the host object in some
    way.

    Example: A coat could be thought of as a component. It stands on its own,
    but you (the host) add it to yourself, and it changes your temperature,
    changes your appearance, adds weight, provides storage, etc.
    """
    @classmethod
    def implements_hook(cls, hook):
        func = getattr(cls, hook, None)
        if func is not None and getattr(func, 'is_hook', False):
            return True
        return False


class Componentized(object):
    """
    An object that can be composed of components.

    NOTE: init will pass arguments along to super().__init__. Therefore, either
    make sure another class descendant from object eliminates init arguments
    before Componentized, or do not pass arguments to init. The best thing is
    to just specify Componentized in the list of classes before another object
    descendant that will consume any init arguments.
    """
    components = []

    def __init__(self, *args, **kwargs):
        self.components = []
        super(Componentized, self).__init__(*args, **kwargs)

    def _init_components(self):
        if 'components' not in self.__dict__:
            self.components = []

    def add_component(self, component):
        self._init_components()
        if component not in self.components:
            self.components.append(component)

    def remove_component(self, component):
        self._init_components()
        if component in self.components:
            self.components.remove(component)

    def get_components(self, parent=Component):
        return filter(lambda c: isinstance(c, parent), self.components)

    def component_hook_implementations(self, hook, parent=Component):
        return OrderedDict([(c, getattr(c, hook))
                            for c in self.get_components(parent)
                            if c.implements_hook(hook)])

    def invoke_component_hook(self, hook, *a, **kw):
        parent = kw.get('parent', Component)
        impl = self.component_hook_implementations(hook, parent=parent)
        return OrderedDict([(c, h(*a, **kw)) for c, h in impl])


class Composed(Decorated, Componentized):
    """
    A class unifying the Decorators and Components.
    """
    def hook_implementations(self, hook):
        impl = self.decorator_hook_implementations(hook)
        impl.update(self.component_hook_implementations(hook))
        return impl

    def invoke_hook(self, hook, *a, **kw):
        results = self.invoke_decorator_hook(hook, *a, **kw)
        results.update(self.invoke_component_hook(hook, *a, **kw))
        return results
