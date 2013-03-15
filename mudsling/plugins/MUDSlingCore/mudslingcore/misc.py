from mudsling.objects import Object


def parse_names(input):
    """
    Parse user input into a list of string aliases.
    @rtype: list
    """
    names = filter(lambda x: x, map(str.strip, input.split(',')))
    if not len(names):
        raise Exception("Invalid name spec")
    return names


def teleport_object(obj, dest):
    """
    Shared function to teleport objects of type mudsling.objects.Object from
    anywhere to another location. This is a detached function because teleport
    is a mudslingcore concept, but it can act on any child of Object.

    Teleporting is different than moving primariliy in that it emits a specific
    set of messages before and after.

    @param obj: The object to teleport.
    @type obj: mudsling.objects.Object

    @param dest: The destination to teleport to.
    @type dest: mudsling.objects.Object
    """
    if obj.isValid(Object) and dest.isValid(Object):
        obj.emitMessage('teleport_out', actor=obj, dest=dest)
        obj.moveTo(dest)
        obj.emitMessage('teleport_in', actor=obj, dest=dest)
