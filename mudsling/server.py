"""
This is the entry point for the twisted application.

DO NOT IMPORT THIS FILE FROM GAME CODE.

You can, however, import this from an interactive shell to access a loaded game
instance.
"""

from twisted.application.service import Application
from mudsling.core import MUDSling

# Setup the twisted application and startup the MUDSling server. Twistd needs
# to find a module-level global variable named 'application' to work.
application = Application("MUDSling Game Server")

# Instantiating the MUDSling class starts up the game and its various services.
game = MUDSling(app=application)
