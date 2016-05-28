import inspect

from mudsling.utils.object import ascend_mro


def hook(*hook_names):
    """
    Decorator to designate a method as a hook implementation.

    :param hook_names: The name of any hooks this method should fire for.
    :type hook_names: list[str]
    """
    def decorate(f):
        try:
            hooks = f.hooks
        except AttributeError:
            f.hooks = []
            hooks = f.hooks
        hooks.extend(hook_names)
        return f
    return decorate


def invoke_hook(obj, hook_name, *a, **kw):
    """
    Traverse obj's MRO, firing any implementation of the named hook.

    Every class in the MRO will fire their implementation, if it exists.
    Overriding on a child class DOES NOT prevent a parent class's implementation
    from firing.

    :param obj: The object on which to invoke the hook.
    :param hook_name: The name of the hook to invoke.
    :param a: Positional arguments to pass to hook implementations.
    :param kw: Keyword arguments to pass to hook implementations.

    :return: Ordered dictionary of hook responses keyed by class.
    :rtype: dict
    """
    from mudsling.storage import ObjRef
    obj = obj._real_object() if isinstance(obj, ObjRef) else obj
    results = {}
    for cls in ascend_mro(obj):
        implementations = hook_implementations(cls).get(hook_name, [])
        if implementations:
            results[cls] = []
        for impl in implementations:
            if impl.__self__ is None:  # Instance method, pass self param.
                results[cls].append(impl(obj, *a, **kw))
            else:  # Class method, cls param is automatic.
                results[cls].append(impl(*a, **kw))
    return results


hook_impl_cache = {}


def hook_implementations(cls, reset=False):
    """
    Get a dictionary of hook implementations for the given class.

    :param cls: The class whose hook implementations to get.
    :param reset: Whether to reset the cache of hook implementations.

    :rtype: dict[str,list]
    """
    if cls in hook_impl_cache and not reset:
        impls = hook_impl_cache[cls]
    else:
        impls = {}
        for attr_name in cls.__dict__.iterkeys():
            attr = getattr(cls, attr_name, None)
            if is_hook_implementation(attr, cls):
                for hook_name in attr.hooks:
                    if hook_name not in impls:
                        impls[hook_name] = []
                    impls[hook_name].append(attr)
        hook_impl_cache[cls] = impls
    return impls


def is_hook_implementation(method, cls=None):
    """
    Determine if the method is a hook implementation, optionally for a specific
    class.

    :param method: The method to inspect.
    :param cls: Optional class to limit evaluation to.
    :rtype: bool
    """
    hooks = getattr(method, 'hooks', [])
    if inspect.ismethod(method) and len(hooks):
        if cls is not None:
            return method.im_class == cls
        return True
    return False
