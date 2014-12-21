import json
import yaml
from xml.etree import ElementTree

from twisted.application.internet import TCPServer, SSLServer
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.internet import ssl
from OpenSSL import SSL

from corepost.routing import RequestRouter
from corepost.enums import Http, HttpHeader, MediaType

import mudsling
from mudsling.config import config
from mudsling.extensibility import TwistedServicePlugin
from mudsling.utils.sequence import flatten
from mudsling.utils.serialization import json_decode_dict

import restserver
from restserver import RESTResource, RESTService, route


class RequestRouterASCII(RequestRouter):
    """Custom implementation to avoid JSON Unicode."""

    def __init__(self, restServiceContainer, schema=None, filters=()):
        RequestRouter.__init__(self, restServiceContainer, schema, filters)
        self._decoder = json.JSONDecoder(object_pairs_hook=json_decode_dict)

    def _RequestRouter__parseRequestData(self, request):
        """Automatically parses JSON,XML,YAML if present"""
        ct = HttpHeader.CONTENT_TYPE
        if (request.method in (Http.POST, Http.PUT)
                and ct in request.received_headers.keys()):
            contentType = request.received_headers["content-type"]
            if contentType == MediaType.APPLICATION_JSON:
                try:
                    # request.json = json.loads(request.content.read())
                    request.json = self._decoder.decode(request.content.read())
                except Exception as ex:
                    raise TypeError("Unable to parse JSON body: %s" % ex)
            elif contentType in (
                    MediaType.APPLICATION_XML, MediaType.TEXT_XML):
                try:
                    request.xml = ElementTree.XML(request.content.read())
                except Exception as ex:
                    raise TypeError("Unable to parse XML body: %s" % ex)
            elif contentType == MediaType.TEXT_YAML:
                try:
                    request.yaml = yaml.safe_load(request.content.read())
                except Exception as ex:
                    raise TypeError("Unable to parse YAML body: %s" % ex)


class RESTResourceASCII(RESTResource):
    """Custom implementation to avoid JSON Unicode."""

    def __init__(self, services=(), schema=None, filters=()):
        self.services = services
        self._RESTResource__router = RequestRouterASCII(self, schema, filters)
        # Skip immediate parent on purpose.
        Resource.__init__(self)


class RESTServer(Site):
    def __init__(self, services, *a, **kw):
        Site.__init__(self, RESTResourceASCII(flatten(services), *a, **kw))

    def getResourceFor(self, request):
        request.setHeader('Server', 'MUDSling/%s' % mudsling.version)
        return Site.getResourceFor(self, request)


class RESTServerPlugin(TwistedServicePlugin):
    def get_service(self):
        RESTService.game = self.game
        factory = RESTServer(self.game.invoke_hook('rest_services'))
        port = self.options.getint('port')
        if self.options.getboolean('ssl'):
            ctx_factory = ssl.DefaultOpenSSLContextFactory(
                self.game.game_file_path(self.options.get('private key')),
                self.game.game_file_path(self.options.get('certificate')),
                sslmethod=SSL.TLSv1_METHOD
            )
            service = SSLServer(port, factory, ctx_factory)
        else:
            service = TCPServer(port, factory)
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
        autokeys = {k: map(str.strip, a.split(','))
                    for k, a in config['autokeys']}
        restserver.generate_autokeys(autokeys)


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
