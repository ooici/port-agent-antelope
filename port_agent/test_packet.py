#!/usr/bin/env python

import unittest
from pprint import pprint

import mock

from packet import makepacket, ReceivedPacket, HEADER_SIZE

TESTPKT1 = bytearray(b'\xa3\x9dz\x00\x00\x10\x00@@\xc8\x1c\x80\x00\x00\x00\x00')

class Test_makepacket(unittest.TestCase):
    def setUp(self):
        pass

    def test_makepacket(self):
        r = makepacket(0, 12345, [])
        self.assertEquals(len(r), 16)
        self.assertEquals([r[6], r[7]], [0x0, 0x40])
        self.assertEquals(r, TESTPKT1)

class Test_ReceivedPacket(unittest.TestCase):
    def test_ReceivedPacket(self):
        buf = bytearray(TESTPKT1)
        pkt = ReceivedPacket(buf)
        pkt.validate(bytearray())


class Test_Both(unittest.TestCase):
    def test_both(self):
        timestamp = 123.456
        msgtype = 222
        data = 'hello, world.'
        txpktbuf = makepacket(msgtype, timestamp, data)
        rxpktbuf = txpktbuf
        rxpktobj = ReceivedPacket(rxpktbuf[:HEADER_SIZE])
        rxpktobj.validate(rxpktbuf[HEADER_SIZE:])
        self.assertEquals(timestamp, rxpktobj.timestamp)
        self.assertEquals(msgtype, rxpktobj.msgtype)
        self.assertEquals(data, rxpktobj.data)


if __name__ == '__main__':
    unittest.main()

