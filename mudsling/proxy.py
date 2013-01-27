from twisted.internet.protocol import ServerFactory
from twisted.application import internet
from twisted.protocols.amp import AMP


class AMPServerProtocol(AMP):
    pass


def AMP_server(port):
    factory = ServerFactory()
    factory.protocol = AMPServerProtocol
    service = internet.TCPServer(port, factory)
    service.setName("AMPServer")
    return service
