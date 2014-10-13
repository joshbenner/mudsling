import hashlib

from twisted.web.http import Request

# For convenient imports in implementing code.
from corepost import *
from corepost.web import *

import mudsling
from mudsling.utils.string import random_string
from mudsling.utils.time import nowutc


# Key store injected by plugin upon load.
#: :type: dict of (str, APIKey)
apikeys = None


def register_api_key(key):
    apikeys[key.id] = key


def get_player_api_keys(player):
    player = player.ref()
    return [k for k in apikeys.itervalues() if k.player == player]


def authenticate(func):
    """
    Decorator to flag a method as requiring authentication.
    """
    def func_wrapper(service, request, *a, **kw):
        authenticate_request(request)
        return func(service, request, *a, **kw)
    return func_wrapper


def authenticate_request(request):
    """
    Called for a request that requires authentication via API key signature.

    Calls will result in request having additional attributes:
    - authenticated: bool
    - player: None or Player

    :param request: The request to authenticate.
    :type request: Request

    :return: Whether or not the request has passed authentication.
    :rtype: bool
    """
    request.authenticated = False
    request.player = None
    raise NotImplementedError()


class AccessDeniedException(RESTException):
    def __init__(self, resourceName):
        if isinstance(resourceName, Request):
            resourceName = resourceName.method + ' ' + resourceName.uri
        super(AccessDeniedException, self).__init__(
            Response(403, "Access denied to %s" % resourceName))


class RESTService(object):
    """
    Generic REST service that plugins can use to expose routes.
    """
    path = None

    #: :type: mudsling.core.MUDSling
    game = None


class APIKey(object):
    """
    Represents an API key issued to a player.
    """
    player = None
    id = None
    key = None
    valid = False
    date_issued = None

    def __init__(self, player):
        self.player = player.ref()
        self.id = random_string(16)
        self.key = random_string(32)
        self.valid = True
        self.date_issued = nowutc()
