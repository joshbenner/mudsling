"""
Object commands.
"""
from mudsling.commands import Command
from mudsling.objects import LockableObject, NamedObject, BaseObject
from mudsling.objects import BasePlayer, Object as LocatedObject
from mudsling import registry
from mudsling import parsers
from mudsling import locks

from mudsling import utils
import mudsling.utils.string

from mudslingcore import misc


class CreateCmd(Command):
    """
    @create <class> called <names>

    Creates a new object of the specified class with the given names.
    """
    aliases = ('@create',)
    lock = 'perm(create objects)'
    syntax = "<class> {called|named|=} <names>"

    def run(self, this, actor, args):
        cls = registry.classes.get_class(args['class'])
        if cls is None:
            actor.msg("Unknown class: %s" % args['class'])
            return
        clsName = registry.classes.get_class_name(cls)
        if not actor.superuser and not (issubclass(cls, LockableObject)
                                        and cls.createLock.eval(cls, actor)):
            msg = "{yYou do not have permission to create {c%s{y objects."
            actor.msg(msg % clsName)
            return
        try:
            names = misc.parse_names(args['names'])
        except Exception as e:
            actor.msg('{r' + e.message)
            return

        obj = cls.create(names=names, owner=actor)
        actor.msg("{gCreated new %s: {c%s" % (clsName, obj.nn))

        if obj.isa(LocatedObject):
            if actor.isa(BasePlayer):
                if (actor.possessing is not None
                        and actor.possessing.isa(LocatedObject)):
                    where = actor.possessing
                else:
                    where = None
            elif actor.isa(LocatedObject):
                where = actor
            else:
                where = None

            if where is not None:
                obj.move_to(where)
                actor.msg("{c%s {yplaced in: {m%s" % (obj.nn, where.nn))
            else:
                actor.msg("{c%s {yis {rnowhere{y.")


class RenameCmd(Command):
    """
    @rename <object> to|as <new-names>

    Renames an object to the new name.
    """
    aliases = ('@rename',)
    syntax = "<object> {to|as} <newNames>"
    arg_parsers = {
        'object': NamedObject,
        'newNames': parsers.StringListStaticParser,
    }
    lock = locks.all_pass  # Everyone can use @rename -- access check within.

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        #: @type: BaseObject
        obj = args['object']
        if not obj.allows(actor, 'rename'):
            actor.tell("{yYou are not allowed to rename {c", obj, "{y.")
            return
        names = args['newNames']
        oldNames = obj.set_names(names)
        msg = "{{gName of {{c#{id}{{g changed to '{{m{name}{{g'"
        keys = {'id': obj.obj_id, 'name': obj.name}
        if len(names) > 1:
            msg += " with aliases: {aliases}"
            aliases = ["{y%s{g" % a for a in obj.aliases]
            keys['aliases'] = utils.string.english_list(aliases)
        actor.msg(str(msg.format(**keys)))
        actor.msg("(previous names: {M%s{n)" % ', '.join(oldNames))


class DeleteCmd(Command):
    """
    @delete <object>

    Deletes the specified object.
    """
    aliases = ('@delete',)
    lock = 'perm(delete objects)'
    syntax = "<object>"

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        # err=True means we'll either exit with error or have single-element
        # list containing the match. Use .ref()... just in case.
        obj = actor.match_object(args['object'], err=True)[0].ref()

        if obj == actor.ref():
            actor.msg("{rYou may not delete yourself.")
            return

        if obj.isa(BaseObject) and not obj.allows(actor, 'delete'):
            actor.tell("{yYou are not allowed to delete {c", obj, "{y.")
            return

        def _do_delete():
            msg = "{c%s {yhas been {rdeleted{y." % obj.nn
            obj.delete()
            actor.msg(msg)

        def _abort_delete():
            actor.msg("{yDelete {gABORTED{y.")

        p = ("{yYou are about to {rDELETE {c%s{y.\n"
             "{yAre you sure you want to {rDELETE {ythis object?")
        actor.player.prompt_yes_no(p % obj.nn,
                                   yes_callback=_do_delete,
                                   no_callback=_abort_delete)


class ClassesCmd(Command):
    """
    @classes

    Displays a list of object classes available.
    """
    aliases = ('@classes',)
    lock = 'perm(create objects)'

    def run(self, this, actor, args):
        out = []
        for name, cls in registry.classes.classes.iteritems():
            pyname = '%s.%s' % (cls.__module__, cls.__name__)
            if name == pyname:
                continue  # Skip python name aliases.
            desc = self._class_desc(cls)
            out.append("{c%s {n[{m%s{n]\n%s" % (name, pyname, desc))
        actor.msg('\n\n'.join(out))

    def _class_desc(self, cls):
        """
        Return just the syntax portion of the command class's docstring.

        @return: Syntax string
        @rtype: str
        """
        trimmed = utils.string.trim_docstring(cls.__doc__)
        desc = []
        for line in trimmed.splitlines():
            if line == "":
                break
            desc.append('  ' + line)
        return '\n'.join(desc)


class GoCmd(Command):
    """
    @go <location>

    Teleport one's self to the indicated location.
    """
    aliases = ('@go',)
    syntax = "<where>"
    lock = 'perm(teleport)'
    arg_parsers = {
        'where': parsers.MatchObject(cls=LocatedObject,
                                     search_for='location', show=True)
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        if actor.is_possessing and actor.possessing.is_valid(LocatedObject):
            #: @type: mudsling.objects.Object
            obj = actor.possessing
            if not obj.allows(actor, 'move'):
                actor.tell("{yYou are not allowed to move {c", obj, "{y.")
                return
            misc.teleport_object(obj, args['where'])
        else:
            m = "You are not attached to a valid object with location."
            raise self._err(m)


class MoveCmd(Command):
    """
    @move <object> to <location>

    Moves the specified object to the specified location.
    """
    aliases = ('@move', '@tel', '@teleport')
    syntax = "<what> to <where>"
    lock = "perm(teleport)"
    arg_parsers = {
        'what':  parsers.MatchObject(cls=LocatedObject,
                                     search_for='locatable object', show=True),
        'where': parsers.MatchObject(cls=LocatedObject,
                                     search_for='location', show=True),
    }

    def run(self, this, actor, args):
        """
        @type this: L{mudslingcore.objects.Player}
        @type actor: L{mudslingcore.objects.Player}
        @type args: C{dict}
        """
        obj, where = (args['what'], args['where'])
        if not obj.allows(actor, 'move'):
            actor.tell("{yYou are not allowed to move {c", obj, "{y.")
            return
        misc.teleport_object(obj, where)
