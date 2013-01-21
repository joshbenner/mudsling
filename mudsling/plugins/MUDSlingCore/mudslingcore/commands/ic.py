"""
The basic commands to enable a character to do the essentials in a game, such
as movement and looking at things.
"""
from mudsling.commands import Command
from mudslingcore.objects import Object


class LookCmd(Command):
    aliases = ('l(?:ook)?',)
    args = ('any', '?at', 'any')

    def run(self, this, input, actor):
        """
        @type this: mudslingcore.objects.Character
        @type input: mudsling.parse.ParsedInput
        @param actor: mudslingcore.objects.Player
        """
        if not input.argstr:
            # Naked look.
            if isinstance(actor.location, Object):
                actor.msg(actor.location.seenBy(actor))
                return
            actor.msg("You don't seem to see anything...")
            return

        #: @type: Object
        target = input.dobj or input.iobj

        if not self.game.db.isValid(target, Object):
            search = input.dobjstr or input.iobjstr
            actor.msg("You do not see any '%s' here." % search)
            return

        actor.msg(target.seenBy(actor))
