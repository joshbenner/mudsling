"""
Object commands.
"""
from mudsling.storage import StoredObject
from mudsling.commands import Command
from mudsling.objects import BasePlayer, Object as LocatedObject
from mudsling import registry
from mudsling import parsers
from mudsling import errors

from mudsling import utils
import mudsling.utils.string

from mudslingcore import misc


class CreateCmd(Command):
    """
    @create <class> called <names>

    Creates a new object of the specified class with the given names.
    """
    aliases = ('@create',)
    required_perm = 'create objects'
    syntax = "<class> {called|named|=} <names>"

    def run(self, this, actor, args):
        cls = registry.classes.getClass(args['class'])
        if cls is None:
            actor.msg("Unknown class: %s" % args['class'])
            return
        try:
            names = misc.parse_names(args['names'])
        except Exception as e:
            actor.msg('{r' + e.message)
            return

        obj = self.game.db.createObject(cls, names[0], names[1:])
        clsName = registry.classes.getClassName(cls)
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
                obj.moveTo(where)
                actor.msg("{c%s {yplaced in: {m%s" % (obj.nn, where.nn))
            else:
                actor.msg("{c%s {yis {rnowhere{y.")


class RenameCmd(Command):
    """
    @rename <object> to|as <new-names>

    Renames an object to the new name.
    """
    aliases = ('@rename',)
    required_perm = 'edit objects'
    syntax = "<object> {to|as} <newNames>"
    arg_parsers = {
        'object': StoredObject,
        'newNames': parsers.StringListStaticParser,
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        #: @type: StoredObject
        obj = args['object']
        names = args['newNames']
        oldNames = obj.setNames(names)
        msg = "{{gName of {{c#{id}{{g changed to '{{m{name}{{g'"
        keys = {'id': obj.id, 'name': obj.name}
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
    required_perm = 'delete objects'
    syntax = "<object>"

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        # err=True means we'll either exit with error or have single-element
        # list containing the match. Use .ref()... just in case.
        obj = actor.matchObject(args['object'], err=True)[0].ref()

        if obj == actor.ref():
            actor.msg("{rYou may not delete yourself.")
            return

        def _do_delete():
            msg = "{c%s {yhas been {rdeleted{y." % obj.nn
            self.game.db.deleteObject(obj)
            actor.msg(msg)

        def _abort_delete():
            actor.msg("{yDelete {gABORTED{y.")

        p = ("{yYou are about to {rDELETE {c%s{y.\n"
             "{yAre you sure you want to {rDELETE {ythis object?")
        actor.player.promptYesNo(p % obj.nn,
                                 yesCallback=_do_delete,
                                 noCallback=_abort_delete)


class ClassesCmd(Command):
    """
    @classes

    Displays a list of object classes available.
    """
    aliases = ('@classes',)
    required_perm = 'create objects'

    def run(self, this, actor, args):
        out = []
        for name, cls in registry.classes.classes.iteritems():
            desc = self._classDesc(cls)
            out.append("{c%s{n\n%s" % (name, desc))
        actor.msg('\n\n'.join(out))

    def _classDesc(self, cls):
        """
        Return just the syntax portion of the command class's docstring.

        @return: Syntax string
        @rtype: str
        """
        trimmed = utils.string.trimDocstring(cls.__doc__)
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
    required_perm = "teleport self"
    arg_parsers = {
        'where': parsers.MatchObject(cls=LocatedObject,
                                     searchFor='location', show=True)
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        if actor.isPosessing and actor.possessing.isValid(LocatedObject):
            #: @type: mudsling.objects.Object
            obj = actor.possessing
            misc.teleport_object(obj, args['where'])
        else:
            raise errors.CommandError("You are not attached to a valid object"
                                      " with location.")


class MoveCmd(Command):
    """
    @move <object> to <location>

    Moves the specified object to the specified location.
    """
    aliases = ('@move', '@tel', '@teleport')
    syntax = "<what> to <where>"
    required_perm = "teleport anything"
    arg_parsers = {
        'what': parsers.MatchObject(cls=LocatedObject,
                                    searchFor='locatable object', show=True),
        'where': parsers.MatchObject(cls=LocatedObject,
                                     searchFor='location', show=True),
    }

    def run(self, this, actor, args):
        """
        @type this: mudslingcore.objects.Player
        @type actor: mudslingcore.objects.Player
        @type args: dict
        """
        misc.teleport_object(args['what'], args['where'])
