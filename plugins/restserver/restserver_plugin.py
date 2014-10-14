from twisted.application.internet import TCPServer
from twisted.web.server import Site

import mudsling
from mudsling.config import config
from mudsling.extensibility import TwistedServicePlugin
from mudsling.utils.sequence import flatten

import restserver
from restserver import RESTResource, RESTService, route, authenticate, APIKey


class RESTServer(Site):
    def __init__(self, services, *a, **kw):
        Site.__init__(self, RESTResource(flatten(services), *a, **kw))

    def getResourceFor(self, request):
        request.setHeader('Server', 'MUDSling/%s' % mudsling.version)
        return Site.getResourceFor(self, request)


class RESTServerPlugin(TwistedServicePlugin):
    def get_service(self):
        RESTService.game = self.game
        factory = RESTServer(self.game.invoke_hook('rest_services'))
        service = TCPServer(self.options.getint('port'), factory)
        service.setName('REST Server')
        return service

    def rest_services(self):
        """
        Return an iterable of rest services.
        """
        return StatusRESTService(),

    def database_loaded(self):
        if not self.game.has_setting('api keys'):
            self.game.set_setting('api keys', {})
        restserver.apikeys = self.game.get_setting('api keys')


class StatusRESTService(RESTService):
    """
    Simple example service.
    """
    path = '/status'

    @route('/')
    @authenticate
    def get(self, request):
        return {
            'site name': config['Main']['name'],
            'software': 'MUDSling',
            'version': mudsling.version,
            'enabled plugins': [p.info.machine_name
                                for p in self.game.plugins.active_plugins()]
        }
