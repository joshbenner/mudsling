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
        actor.msg(repr(args))
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
                actor.msg("{c%s {y placed in: {m%s" % (obj.nn, where.nn))
            else:
                actor.msg("{c%s {yis {rnowhere{y.")
