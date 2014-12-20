#!/usr/bin/env python

from cPickle import dumps
import logging

import gevent
from gevent import Greenlet, spawn, sleep
from gevent.event import Event

from ooi.logging import log

from servers import DataServer, CmdServer
import ntp
from orbpkt2dict import orbpkt2dict
from orbpktsrc import OrbPktSrc
from packet import makepacket, PacketType

from version import __version__

LISTENING_ADDR = ''


def transform(orbpkt):
    d = orbpkt2dict(orbpkt)
    return dumps(d, 2)


class OrbPktSrcError(Exception): pass


class PortAgent(Greenlet):
    def __init__(self, cfg, cmdproc):
        super(PortAgent, self).__init__()
        self.cfg = cfg
        self.cmdproc = cmdproc
        self.heartbeat_event = Event()
        self.cmdproc.setCmd('get_state', None, self.get_state)
        self.cmdproc.setCmd('ping', None, self.ping)
        self.cmdproc.setCmd('shutdown', None, self.shutdown)
        self.states = {
            self.state_startup: 'STARTUP',
            self.state_unconfigured: 'UNCONFIGURED',
            self.state_configured: 'CONFIGURED',
            self.state_connected: 'CONNECTED',
        }

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, v):
        self._state = v
        log.debug("Transitioning to state %s" % v)

    def janitor(self, src):
        log.debug("Janitor, cleanup aisle 12")
        self.kill(src.exception)

    def heartbeat_timer(self):
        try:
            while True:
                self.cfg.heartbeatactive.wait()
                sleep(self.cfg.heartbeat_interval)
                self.heartbeat_event.set()
                self.heartbeat_event.clear()
        except Exception:
            log.critical("heartbeat_timer terminating due to exception", exc_info=True)
            raise

    def _run(self):
        try:
            self.state = self.state_startup
            while True:
                self.state = self.state()
        except Exception:
            log.critical("PortAgent terminating due to exception", exc_info=True)
            raise
        finally:
            log.debug("Killing orbpkt src")
            try: self.orbpktsrc.kill()
            except: pass
            log.debug("Stopping dataserver")
            try: self.dataserver.stop()
            except: pass
            log.debug("Stopping cmdserver")
            try: self.cmdserver.stop()
            except: pass
            log.debug("PortAgent finally done")

    def state_startup(self):
        # start cmdserver; err if not cmd port
        spawn(self.heartbeat_timer).link_exception(self.janitor)
        self.cmdserver = CmdServer((LISTENING_ADDR, self.cfg.command_port),
                                   self.cmdproc.processCmds, self.janitor)
        self.cmdserver.start()
        return self.state_unconfigured

    def state_unconfigured(self):
        self.cfg.configuredevent.wait()
        return self.state_configured

    def state_configured(self):
        # spawn orbreapthr
        # link to it? what if it dies?
        self.orbpktsrc = OrbPktSrc(
            srcname = self.cfg.antelope_orb_name,
            select = self.cfg.antelope_orb_select,
            reject = self.cfg.antelope_orb_reject,
            after = self.cfg.antelope_orb_after,
            transformation = transform
        )
        self.orbpktsrc.link_exception(self.janitor)
        self.orbpktsrc.start()
        # spawn data server
        self.dataserver = DataServer(
                (LISTENING_ADDR, self.cfg.data_port),
                self.orbpktsrc.subscription,
                self.heartbeat_event, self.janitor)
        self.dataserver.start()
        # spawn state_connected
        return self.state_connected

    def state_connected(self):
        # on dataserver config update event
        self.cfg.dataserverconfigupdate.wait()
        self.orbpktsrc.kill()
        self.dataserver.stop()
        return self.state_configured

    def get_state(self, val, sock):
        statestr = self.states[self.state]
        sock.sendall(makepacket(PacketType.PORT_AGENT_STATUS, ntp.now(), statestr))

    def ping(self, val, sock):
        msg = "pong. version: " + __version__
        sock.sendall(makepacket(PacketType.PORT_AGENT_STATUS, ntp.now(), msg))

    def shutdown(self, val, sock):
        self.kill()

    # no state_disconnected; orbreapthr doesn't ever disconnect or even report
    # errors; there are various approaches we could take to try to beat it into
    # shape, if necessary.

