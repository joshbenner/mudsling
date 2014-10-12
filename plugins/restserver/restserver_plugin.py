from twisted.application.internet import TCPServer
from twisted.web.server import Site

import mudsling
from mudsling.config import config
from mudsling.extensibility import TwistedServicePlugin
from mudsling.utils.sequence import flatten

from restserver import *


class RESTServer(Site):
    def __init__(self, services, *a, **kw):
        Site.__init__(self, RESTResource(flatten(services), *a, **kw))


class RESTServerPlugin(TwistedServicePlugin):
    def get_service(self):
        RESTService.game = self.game
        factory = RESTServer(self.game.invoke_hook('rest_services',
                                                   plugin_type=None))
        service = TCPServer(self.options.getint('port'), factory)
        service.setName('REST Server')
        return service

    def rest_services(self):
        """
        Return an iterable of rest services.
        """
        return StatusRESTService(),


class StatusRESTService(RESTService):
    """
    Simple example service.
    """
    path = '/status'

    @route('/')
    def get(self, request):
        return {
            'site name': config['Main']['name'],
            'software': 'MUDSling',
            'version': mudsling.version,
            'enabled plugins': [p.info.machine_name
                                for p in self.game.plugins.active_plugins()]
        }
