from mudsling.objects import BasePlayer, BaseObject, Object
from mudsling import registry
import mudsling.utils.modules as mod_utils


def _isa(accessed_obj, accessing_obj, cls_name):
    cls = registry.classes.get_class(cls_name)
    if cls is None:
        # noinspection PyBroadException
        try:
            cls = mod_utils.class_from_path(cls_name)
        except:
            cls = None
        if not issubclass(cls, BaseObject):
            cls = None
    if cls is not None:
        return accessing_obj.isa(cls)
    return False


def can_touch(obj, who):
    return who.isa(Object) and who.can_touch(obj)


def can(obj, who, op):
    return obj.allows(who, op)


def default_funcs():
    """
    Return a map of default/built-in lock functions. These can be overridden by
    plugins via lock_functions().

    MUDSling lock function signature:
        func(accessedObj, accessingObj, *args)
    """
    true = lambda *a: True
    false = lambda *a: False
    id = lambda o, w, id: w.obj_id == int(id)
    perm = lambda o, w, p: w.has_perm(p)
    return {
        'id': id,
        'dbref': id,
        'true': true,
        'all': true,
        'false': false,
        'none': false,
        'perm': perm,
        'has_perm': perm,
        'player': lambda o, w: w.is_valid(BasePlayer),
        'self': lambda o, w: o.ref() == w.ref(),
        'owner': lambda o, w: (o.owner == w.ref()
                               if o.owner is not None else False),
        'class': _isa,
        'isa': _isa,
        'can_touch': can_touch,
        'can': can,
    }
