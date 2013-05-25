"""
Transparent composition of classes and instances.

Features act a lot like multiple parent classes, but they cannot interact with
eachother via super(), and they can be easily added to or removed from classes
AND instances at run time.
"""
import inspect
import types


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
    pass


class FeaturedObject(object):
    """
    An object with features.

    Features are collected from the instance, and all classes in the MRO of the
    instance.
    """
    _features = []

    def __init__(self, *args, **kwargs):
        self._features = []
        for feature in self.features:
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

    def add_feature(self, feature):
        if feature in self._features:
            return
        self._features.append(feature)

    def remove_feature(self, feature):
        if feature in self._features:
            self._features.remove(feature)

    def __getattr__(self, name):
        for feature in self._features:
            try:
                val = getattr(feature, name)
            except AttributeError:
                continue
            else:
                if inspect.ismethod(val):
                    bind_to = val.im_self or self
                    val = types.MethodType(val.im_func, bind_to)
                return val
        clsname = self.__class__.__name__
        msg = "'%s' object has no attribute '%s'" % (clsname, name)
        raise AttributeError(msg)

    @property
    def features(self):
        features = []
        if '_features' in self.__dict__:
            features.extend(self._features)
        for cls in self.__class__.__mro__:
            if issubclass(cls, FeaturedObject) and '_features' in cls.__dict__:
                for feature in cls._features:
                    if feature not in features:
                        features.append(feature)
        return features
