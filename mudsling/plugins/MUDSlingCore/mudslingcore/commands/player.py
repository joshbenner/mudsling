"""
Player commands.
"""
from mudsling.commands import Command


class EvalCmd(Command):
    """
    @eval <python code> -- Executes arbitrary python code.

    Requires the 'eval code' permission.
    """
    aliases = ('@eval',)
    args = ('any', None, None)

    def prepare(self):
        """
        Compile the code and handle errors.
        """

    def run(self):
        """
        Execute and time the code.
        """
