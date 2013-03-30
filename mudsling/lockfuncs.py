from mudsling.objects import BasePlayer


def defaultFuncs():
    """
    Return a map of default/built-in lock functions. These can be overridden by
    plugins via hook_lockFunctions().

    MUDSling lock function signature:
        func(accessedObj, accessingObj, *args)
    """
    true = lambda *a: True
    false = lambda *a: False
    id = lambda o, w, id: w.id == id
    perm = lambda o, w, p: o.hasPerm(p)
    return {
        'id': id,
        'dbref': id,
        'true': true,
        'all': true,
        'false': false,
        'none': false,
        'perm': perm,
        'hasPerm': perm,
        'has_perm': perm,
        'player': lambda o, w: w.isValid(BasePlayer),
        'self': lambda o, w: o.ref() == w.ref()
    }
