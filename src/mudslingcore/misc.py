from pkg_resources import resource_filename

from mudsling.objects import Object


def migrations_path(name):
    # Resources are not paths, and should not be manipulated with os.path.
    return '%s/%s' % (resource_filename(__name__, 'schemas'), name)


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
    if obj.is_valid(Object) and dest.is_valid(Object):
        obj.emit_message('teleport_out', actor=obj, dest=dest)
        obj.move_to(dest)
        obj.emit_message('teleport_in', actor=obj, dest=dest)
