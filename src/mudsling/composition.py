"""
Modular composition of classes and instances.

Decorators are classes that extend the functionality of other classes or even
instances.

Decorators can be easily added to and removed from classes and instances. They
are useful when host objects offer mixins opportunities to extend
their functionality, such as invoking hooks on mixins or collecting
mixin data (ie: mixin-provided commands).

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


class Mixin(object):
    """
    Mixins are classes that provide attributes and methods to be accessible
    by instances they are associated with (at class or instance level).

    Mixins are not supposed to be instanced, because their attributes are
    transparently proxied to be accessible by instances that have access to
    them.

    Example: If you learn math, that becomes a mixins of your person. You do
    not possess an instance of math, but rather math knowledge is now a part of
    your mind, its processes are available to you, and it stores information in
    you, such as which concepts you understand, a running tab when counting,
    and so on.

    You may write a Mixin largely like you would write a parent class, but
    there are some notable differences:
    * _init_mixin is called during HasMixins initialization.
    * Special attribute methods like __getattr__ are never called.
    * Decorators are not in the instance MRO, and are not searched by super().
    * Mixin methods may not use super(). If mixins use inheritance, you
        must use composed parent calls instead: parentClass.same_method(*args)
    """
    @classmethod
    def _mixin_attr(cls, name, owner):
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

    def _init_mixin(self, *a, **kw):
        # Stop init here. Decorators should be last parents.
        pass


class HasMixins(object):
    """
    An object with mixins.

    Mixins are collected from the instance, and all classes in the MRO of
    the instance.
    """
    _mixins = []

    @classmethod
    def _init_class_mixins(cls):
        if '_mixins' not in cls.__dict__:
            cls._mixins = []

    @classmethod
    def add_class_mixin(cls, mixin):
        cls._init_class_mixins()
        cls._mixins.append(mixin)

    @classmethod
    def remove_class_mixin(cls, mixin):
        cls._init_class_mixins()
        if mixin in cls._mixins:
            cls._mixins.remove(mixin)

    @classmethod
    def get_class_mixins(cls, parent=Mixin):
        mixins = []
        for c in cls.__mro__:
            if issubclass(c, HasMixins) and '_mixins' in c.__dict__:
                mixins.extend(f for f in c._mixins if issubclass(f, parent)
                              and not f in mixins)
        return mixins

    def __init__(self, *args, **kwargs):
        self._mixins = []
        for dec in self.mixins:
            if '__init__' in dec.__dict__:
                dec.__init__.im_func(self, *args, **kwargs)
        super(HasMixins, self).__init__(*args, **kwargs)

    @property
    def mixins(self):
        return self.get_mixins()

    def add_mixin(self, mixin):
        if mixin in self._mixins:
            return
        self._mixins.append(mixin)

    def remove_mixin(self, mixin):
        if mixin in self._mixins:
            self._mixins.remove(mixin)

    def has_mixin(self, mixin):
        return mixin in self.mixins

    def __getattr__(self, name):
        for mixin in (f for f in self.mixins if hasattr(f, name)):
            return mixin._mixin_attr(name, self)
        clsname = self.__class__.__name__
        msg = "'%s' object has no attribute '%s'" % (clsname, name)
        raise AttributeError(msg)

    def get_mixins(self, parent=Mixin):
        """
        Get a list of mixins associated with this instance.

        :param parent: An optional parent class by which to filter mixins.

        :rtype: list
        """
        mixins = filter(lambda f: issubclass(f, parent),
                        getattr(self, '_mixins', []))
        mixins.extend(self.__class__.get_class_mixins(parent=parent))
        return mixins

    def mixin_hook_implementations(self, hook, parent=Mixin):
        impl = OrderedDict()
        for mixin in self.get_mixins(parent=parent):
            if mixin.implements_hook(hook):
                func = getattr(mixin, hook)
                bind = func.im_self or self
                impl[mixin] = types.MethodType(func.im_func, bind)
        return impl

    def invoke_mixin_hook(self, hook, *a, **kw):
        parent = kw.get('parent', Mixin)
        impl = self.mixin_hook_implementations(hook, parent=parent)
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


class Composed(HasMixins, Componentized):
    """
    A class unifying the Decorators and Components.
    """
    def hook_implementations(self, hook):
        impl = self.mixin_hook_implementations(hook)
        impl.update(self.component_hook_implementations(hook))
        return impl

    def invoke_hook(self, hook, *a, **kw):
        results = self.invoke_mixin_hook(hook, *a, **kw)
        results.update(self.invoke_component_hook(hook, *a, **kw))
        return results
