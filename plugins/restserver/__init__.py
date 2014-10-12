# For convenient imports in implementing code.
from corepost import *
from corepost.web import *


class RESTService(object):
    """
    Generic REST service that plugins can use to expose routes.
    """
    path = None

    #: :type: mudsling.core.MUDSling
    game = None
