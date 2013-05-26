"""
Modular composition of classes and instances.

Features can be easily added to and removed from classes and instances. They
are useful when objects possessing them offer features opportunities to extend
their functionality, such as invoking hooks on features or collecting feature
data (ie: feature-provided commands).

Features can also transparently provide new attributes and methods to classes
and instances they decorate. They are essentially interfaces that come along
with an implementation.
"""
import inspect
import types
from collections import OrderedDict


class Feature(object):
    """
    Features are classes that provide attributes and methods to be accessible
    by instances they are associated with (at class or instance level).

    You may write a Feature largely like you would write a parent class, but
    there are some notable differences:
    * __init__ IS called during FeaturedObject initialization.
    * Special attribute methods like __getattr__ are never called.
    * Features are not in the instance MRO, and are not searched by super().
    * Feature methods may not use super(). If features use inheritance, you
        must use composed parent calls instead: parentClass.same_method(*args)
    """
    @classmethod
    def implements_hook(cls, hook):
        return callable(getattr(cls, hook, None))

    @classmethod
    def _feature_attr(cls, name, owner):
        val = getattr(cls, name)
        if inspect.ismethod(val):
            bind_to = val.im_self or owner
            val = types.MethodType(val.im_func, bind_to)
        return val


class FeaturedObject(object):
    """
    An object with features.

    Features are collected from the instance, and all classes in the MRO of the
    instance.
    """
    _features = []

    def __init__(self, *args, **kwargs):
        self._features = []
        for feature in self._features:
            if '__init__' in feature.__dict__:
                feature.__init__.im_func(self, *args, **kwargs)
        super(FeaturedObject, self).__init__(*args, **kwargs)

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

    def __getattr__(self, name):
        for feature in (f for f in self._features if hasattr(f, name)):
            return feature._feature_attr(name, self)
        clsname = self.__class__.__name__
        msg = "'%s' object has no attribute '%s'" % (clsname, name)
        raise AttributeError(msg)

    @classmethod
    def get_class_features(cls, parent=Feature):
        features = []
        for c in cls.__mro__:
            if issubclass(c, FeaturedObject) and '_features' in c.__dict__:
                features.extend(f for f in c._features if issubclass(f, parent)
                                and not f in features)
        return features

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

    def invoke_hook(self, hook, *a, **kw):
        results = OrderedDict()
        for feature in self.get_features(parent=kw.get('parent', Feature)):
            if feature.implements_hook(hook):
                results[feature] = feature._feature_attr(hook, self)(*a, **kw)
        return results
