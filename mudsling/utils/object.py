from mudsling.objects import BasePlayer, Object


def location(obj):
    """
    Tries to identify a 'location' for the passed object. This is not always
    direct, since the object might be possessing another object. Calling this
    removes the caller's responsibility for knowing what type the object is or
    what state it is in.

    @param obj: The object whose location to find.
    @type obj: mudsling.storage.ObjRef
    @rtype: mudsling.storage.ObjRef or None
    """
    if obj.isa(BasePlayer):
        if obj.possessing is not None:
            return location(obj.possessing)
        return None
    if obj.isa(Object):
        return obj.location
