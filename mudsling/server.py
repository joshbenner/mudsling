"""
This is the entry point for the twisted application. This is also where other
code can get a very handy reference to the running game instance via:

    from mudsling.server import game
"""

from twisted.application.service import Application
from mudsling.core import MUDSling

# Setup the twisted application and startup the MUDSling server. Twistd needs
# to find a module-level global variable named 'application' to work.
application = Application("MUDSling Game Server")

# Instantiating the MUDSling class starts up the game and its various services.
# This is also the means to reference the game, the database, config...
# everything. To use, do:
# >>> from mudsling.server import game
game = MUDSling(app=application)
