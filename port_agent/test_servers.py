#!/usr/bin/env python

from contextlib import closing
import unittest

from mock import Mock, MagicMock

from gevent import sleep, spawn, wait
from gevent.socket import create_connection
from gevent.queue import Queue
from gevent.event import Event

from cmdproc import CmdProcessor
from servers import DataServer, CmdServer
from packet import ReceivedPacket, makepacket, PacketType

DATA_PORT = 54321

class Test_DataServer(unittest.TestCase):
    def janitor(self, *args, **kwargs):
        pass

    def setUp(self):
        self.heartbeat_event = Event()
        self.cfg = Mock()
        self.cfg.data_port = DATA_PORT
        self.q = Queue()
        self.orbpktsrc = MagicMock()
        self.orbpktsrc.subscription.return_value.__enter__.return_value = self.q
        self.ds = DataServer(('localhost', DATA_PORT),
            self.orbpktsrc.subscription, self.heartbeat_event, self.janitor)

    def test_DataServer(self):
        self.cfg.heartbeat_interval = 10
        [self.q.put(('', float(n))) for n in xrange(15)]
        received = []
        def rx():
            try:
                self.ds.start()
                sock = create_connection(('127.0.0.1', DATA_PORT), timeout=2)
                while True:
                    received.append(sock.recv(0x10))
            finally:
                self.ds.stop()
        rxg = spawn(rx)
        sleep(1)
        rxg.kill()
        self.assertEquals(len(received), 15)

    def test_DataServer_heartbeat(self):
        self.cfg.heartbeat_interval = 1
        received = []
        def rx():
            try:
                self.ds.start()
                sock = create_connection(('127.0.0.1', DATA_PORT), timeout=2)
                while True:
                    received.append(sock.recv(0x10))
            finally:
                self.ds.stop()
        rxg = spawn(rx)
        sleep(0.1)
        self.heartbeat_event.set()
        self.heartbeat_event.clear()
        sleep(0.1)
        rxg.kill()
        self.assertEquals(len(received), 1)

class Test_CmdServer(unittest.TestCase):
    def janitor(self, *args, **kwargs):
        pass

    def setUp(self):
        self.cfg = Mock()
        self.cfg.command_port = DATA_PORT
        self.cp = CmdProcessor()
        self.ds = CmdServer(('127.0.0.1', DATA_PORT), self.cp.processCmds, self.janitor)

    def test_CmdServer(self):
        rxcalled = []
        def rx(*args, **kwargs):
            rxcalled.append(True)
        def rx2(val, *args, **kwargs):
            rxcalled.append(True)
            self.assertEquals(val, 123)
        self.cp.setCmd('cmd', None, rx)
        self.cp.setCmd('cmd2', int, rx2)
        def tx():
            try:
                self.ds.start()
                sock = create_connection(('127.0.0.1', DATA_PORT), timeout=2)
                with closing(sock):
                    sock.sendall('cmd\ncmd2 123\n')
                sleep(0)
            finally:
                self.ds.stop()
        txg = spawn(tx)
        wait()
        self.assertTrue(rxcalled[0])
        self.assertTrue(rxcalled[1])

if __name__ == '__main__':
    unittest.main()

