from twisted.internet import reactor, protocol

from packet import HEADER_SIZE

class Protocol(protocol.Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        # log something
        self.state = 'HEADER'
        self.buf = bytearray()

    def connectionLost(self, reason):
        # log something
        pass

    def dataReceived(self, data):
        if self.state == 'HEADER':
            self.got_HEADER(data)
        elif self.state == 'DATA':
            self.got_DATA(data)
        else:
            raise Exception('Invaild state!')

    def got_HEADER(self, data):
        self.buf.extend(data)
        if len(self.buf) >= HEADER_SIZE:
            self.state = 'DATA'
            self.rawbuf = # forget twisted

class Factory(protocol.Factory):
    def __init__(self):
        pass

    def buildProtocol(self, addr):
        return Protocol(self)


