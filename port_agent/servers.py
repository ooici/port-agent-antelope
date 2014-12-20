#!/usr/bin/env python

from contextlib import closing
import errno

from gevent import spawn, socket, getcurrent, sleep
from gevent.coros import Semaphore
import gevent.server

from ooi.logging import log

from packet import (makepacket, ReceivedPacket, HEADER_SIZE, MAX_PACKET_SIZE,
                    PacketType)
import ntp


POOL_SIZE = 100

class SockClosed(Exception): pass

class StreamServer(gevent.server.StreamServer):
    def __init__(self, addr, janitor=None):
        self.addr = addr
        self.janitor = janitor
        super(StreamServer, self).__init__(
            listener = addr,
            spawn = POOL_SIZE
        )

    def start(self, *args, **kwargs):
        log.info("%s listening on %s" % (self.__class__, self.addr))
        super(StreamServer, self).start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        super(StreamServer, self).stop(*args, **kwargs)
        log.info("%s stopped" % self.__class__)

    def handle(self, sock, addr):
        socket_error = ''
        try:
            log.info("%s accepted connection from %s" % (self.__class__, addr,))
            thisgreenlet = getcurrent()
            if self.janitor is not None:
                thisgreenlet.link_exception(self.janitor)
            with closing(sock):
                self.work(sock, addr)
        except SockClosed:
            pass
        except socket.error, e:
            socket_error = e
        except Exception, e:
            log.error("%s connection terminating due to exception %s" %
                                        (self.__class__, addr,), exc_info=True)
            raise
        finally:
            log.info("%s connection closed from %s %s" % (
                            self.__class__, addr, socket_error))

class DataServer(StreamServer):
    def __init__(self, addr, subscription, heartbeat_event, janitor):
        self.subscription = subscription
        self.heartbeat_event = heartbeat_event
        super(DataServer, self).__init__(addr, janitor)

    def work(self, sock, addr):
        socklock = Semaphore()
        heartbeat = spawn(self.heartbeat_sender, sock, addr,
                          socklock, getcurrent())
        heartbeat.link_exception(self.janitor)
        try:
            with self.subscription() as queue:
                while True:
                    orbpkt, timestamp = queue.get()
                    pkt = makepacket(PacketType.DATA_FROM_INSTRUMENT,
                                     timestamp, orbpkt)
                    with socklock:
                        sock.sendall(pkt)
        finally:
            try: heartbeat.kill()
            except: pass

    def heartbeat_sender(self, sock, addr, socklock, parent):
        try:
            with closing(sock):
                while True:
                    self.heartbeat_event.wait()
                    pkt = makepacket(PacketType.PORT_AGENT_HEARTBEAT,
                                     ntp.now(), '')
                    with socklock:
                        sock.sendall(pkt)
                    sleep()
        except socket.error, e:
            log.debug('heartbeat socket err: %s' % e)
        except Exception:
            log.error("heartbeat_sender terminating due to exception", exc_info=True)
            raise
        finally:
            try: parent.kill()
            except: pass


class CmdServer(StreamServer):
    # Note: It's not really clear how cmds are supposed to be framed. Looks
    # like the PA and PAC work "on accident" by relying on 1:1 send/recv
    # behavior, which is not correct with TCP. But whatever we'll do the same
    # thing.
    def __init__(self, addr, process_cmds, janitor):
        self.process_cmds = process_cmds
        super(CmdServer, self).__init__(addr, janitor)

    def work(self, sock, addr):
        cmdstr = ''
        while True:
            rxstr = sock.recv(1024)
            if len(rxstr) == 0:
                self.process_cmds(cmdstr, sock)
                sock.close()
                return
            cmdstr += rxstr

