"""
Object commands.
"""
from mudsling.commands import Command
from mudsling.objects import BasePlayer, Object as LocatedObject

from mudslingcore import misc


class CreateCmd(Command):
    """
    @create <class> <names>

    Creates a new object of the specified class with the given names.
    """
    aliases = ('@create',)
    required_perm = 'create objects'
    syntax = "<class> [called|named] <names>"

    def run(self, this, actor, args):
        cls = self.game.getClass(args['class'])
        if cls is None:
            actor.msg("Unknown class: %s" % args['class'])
            return
        try:
            names = misc.parse_names(args['names'])
        except Exception as e:
            actor.msg('{r' + e.message)
            return

        obj = self.game.db.createObject(cls, names[0], names[1:])
        clsName = self.game.getClassName(cls)
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
        pass
