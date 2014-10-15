from hashlib import sha1
import hmac

from twisted.web.http import Request, stringToDatetime

# For convenient imports in implementing code.
from corepost import *
from corepost.web import *

import mudsling
from mudsling.utils.string import random_string
from mudsling.utils.time import nowutc, get_datetime, unixtime
from mudsling.errors import FailedMatch


# Key store injected by plugin upon load.
#: :type: dict of (str, APIKey)
apikeys = None


def register_api_key(key):
    apikeys[key.id] = key


def get_player_api_keys(player):
    player = player.ref()
    return [k for k in apikeys.itervalues() if k.player == player]


def get_api_key(id):
    if id in apikeys:
        key = apikeys[id]
        return key
    raise InvalidAPIKey()


class InvalidAPIKey(FailedMatch):
    pass


def authenticate(*authorizations):
    """
    Decorator to flag a method as requiring authentication.
    """
    def decorator(f):
        def func_wrapper(service, request, *a, **kw):
            if not authenticate_request(request,
                                        authorizations=authorizations):
                msg = 'Access Denied to %s %s' % (request.method, request.uri)
                return Response(403, msg,
                                headers={'Content-Type': MediaType.TEXT_PLAIN})
            return f(service, request, *a, **kw)
        return func_wrapper
    return decorator


def authenticate_request(request, authorizations=()):
    """
    Called for a request that requires authentication via API key signature.

    Calls will result in request having additional attributes:
    - authenticated: bool
    - apikey: None or Player

    :param request: The request to authenticate.
    :type request: Request

    :return: Whether or not the request has passed authentication.
    :rtype: bool
    """
    request.authenticated = False
    request.apikey = None
    signature = request.getHeader('Signature')
    if signature is not None:
        (key_id, nonce, signed) = signature.split(':')
        try:
            #: :type: restserver.APIKey
            apikey = get_api_key(key_id)
        except InvalidAPIKey:
            pass  # Fall through to Access Denied
        else:
            authorized = True
            for authorization in authorizations:
                if not apikey.is_authorized(authorization):
                    authorized = False
                    break
            if authorized:
                request.apikey = apikey
                date_header = request.getHeader('Date')
                if apikey.valid and date_header:
                    timestamp = stringToDatetime(date_header)
                    offset = abs(unixtime() - timestamp)
                    if offset <= 600:
                        tosign = '\n'.join((
                            request.method,
                            request.uri,
                            date_header,
                            nonce
                        ))
                        hashed = hmac.new(apikey.key, tosign, sha1)
                        verify = hashed.digest().encode('base64')
                        if verify == signed:
                            request.authenticated = True
                            return True
    return False


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
    authorizations = ()

    def __init__(self, player):
        self.player = player.ref()
        self.id = random_string(16)
        self.key = random_string(32)
        self.valid = True
        self.date_issued = nowutc()

    def grant_authorization(self, authorization):
        self.authorizations += (authorization.lower(),)

    def revoke_authorization(self, authorization):
        authorization = authorization.lower()
        self.authorizations = tuple(a for a in self.authorizations
                                    if a != authorization)

    def is_authorized(self, authorization):
        return authorization.lower() in self.authorizations
