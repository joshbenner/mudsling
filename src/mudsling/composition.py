"""
Modular composition of classes and instances.

Features are classes that extend the functionality of other classes or even
instances.

Features can be easily added to and removed from classes and instances. They
are useful when objects possessing them offer features opportunities to extend
their functionality, such as invoking hooks on features or collecting feature
data (ie: feature-provided commands).

Features can also transparently provide new attributes and methods to classes
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
    Generic, hook-implementing decorator. Super class of Feature and Component.
    """
    @classmethod
    def implements_hook(cls, hook):
        func = getattr(cls, hook, None)
        if func is not None and getattr(func, 'is_hook', False):
            return True
        return False


class Feature(Decorator):
    """
    Features are classes that provide attributes and methods to be accessible
    by instances they are associated with (at class or instance level).

    Features are not supposed to be instantiated, because their attributes are
    transparently proxied to be accessible by instances that have access to
    them.

    Example: If you learn math, that becomes a feature of your person. You do
    not possess an instance of math, but rather math knowledge is now a part of
    your mind, its processes are available to you, and it stores information in
    you, such as which concepts you understand, a running tab when counting,
    and so on.

    You may write a Feature largely like you would write a parent class, but
    there are some notable differences:
    * __init__ IS called during Featurized initialization.
    * Special attribute methods like __getattr__ are never called.
    * Features are not in the instance MRO, and are not searched by super().
    * Feature methods may not use super(). If features use inheritance, you
        must use composed parent calls instead: parentClass.same_method(*args)
    """
    @classmethod
    def _feature_attr(cls, name, owner):
        if name.startswith('__'):  # Hide magic attributes.
            raise AttributeError
        val = getattr(cls, name)
        if is_hook(val):  # Hide hooks.
            raise AttributeError
        if inspect.ismethod(val):
            bind_to = val.im_self or owner
            val = types.MethodType(val.im_func, bind_to)
        return val

    def __init__(self, *a, **kw):
        # Stop super propagation of init here. Features should be last parents.
        pass


class Featurized(object):
    """
    An object with features.

    Features are collected from the instance, and all classes in the MRO of the
    instance.
    """
    _features = []

    @classmethod
    def _init_class_features(cls):
        if '_features' not in cls.__dict__:
            cls._features = []

    @classmethod
    def add_class_feature(cls, feature):
        cls._init_class_features()
        cls._features.append(feature)

    @classmethod
    def remove_class_feature(cls, feature):
        cls._init_class_features()
        if feature in cls._features:
            cls._features.remove(feature)

    @classmethod
    def get_class_features(cls, parent=Feature):
        features = []
        for c in cls.__mro__:
            if issubclass(c, Featurized) and '_features' in c.__dict__:
                features.extend(f for f in c._features if issubclass(f, parent)
                                and not f in features)
        return features

    def __init__(self, *args, **kwargs):
        self._features = []
        for feature in self._features:
            if '__init__' in feature.__dict__:
                feature.__init__.im_func(self, *args, **kwargs)
        super(Featurized, self).__init__(*args, **kwargs)

    @property
    def features(self):
        return self.get_features()

    def add_feature(self, feature):
        if feature in self._features:
            return
        self._features.append(feature)

    def remove_feature(self, feature):
        if feature in self._features:
            self._features.remove(feature)

    def has_feature(self, feature):
        return feature in self.features

    def __getattr__(self, name):
        for feature in (f for f in self.features if hasattr(f, name)):
            return feature._feature_attr(name, self)
        clsname = self.__class__.__name__
        msg = "'%s' object has no attribute '%s'" % (clsname, name)
        raise AttributeError(msg)

    def get_features(self, parent=Feature):
        """
        Get a list of features associated with this instance.

        @param parent: An optional parent class by which to filter features.

        @rtype: C{list}
        """
        features = filter(lambda f: issubclass(f, parent),
                          getattr(self, '_features', []))
        features.extend(self.__class__.get_class_features(parent=parent))
        return features

    def feature_hook_implementations(self, hook, parent=Feature):
        impl = OrderedDict()
        for feature in self.get_features(parent=parent):
            if feature.implements_hook(hook):
                func = getattr(feature, hook)
                bind = func.im_self or self
                impl[feature] = types.MethodType(func.im_func, bind)
        return impl

    def invoke_feature_hook(self, hook, *a, **kw):
        parent = kw.get('parent', Feature)
        impl = self.feature_hook_implementations(hook, parent=parent)
        return OrderedDict([(f, h(*a, **kw)) for f, h in impl.iteritems()])


class Component(Decorator):
    """
    A modular piece of functionality which can be hosted by a parent instance.

    Components are supposed to be instantiated and are largely their own
    objects that just happen to enhance or complement the host object in some
    way.

    Example: A coat could be thought of as a component. It stands on its own,
    but you (the host) add it to yourself, and it changes your temperature,
    changes your appearance, adds weight, provides storage, etc.
    """
    pass


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


class Composed(Featurized, Componentized):
    """
    A class unifying the Features and Components.
    """
    def hook_implementations(self, hook):
        impl = self.feature_hook_implementations(hook)
        impl.update(self.component_hook_implementations(hook))
        return impl

    def invoke_hook(self, hook, *a, **kw):
        results = self.invoke_feature_hook(hook, *a, **kw)
        results.update(self.invoke_component_hook(hook, *a, **kw))
        return results
