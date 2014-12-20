#!/usr/bin/env python

from contextlib import closing
import logging
from StringIO import StringIO
from tempfile import NamedTemporaryFile
import unittest

from gevent import spawn, wait, sleep

import mock

from cmdproc import CmdProcessor
from config import Config, DEFAULT_PID_DIR


class Test_Config_Base(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()
        self.cfg = Config(None, self.cp)

class Test_Config(Test_Config_Base):
    def test_Config(self):
        self.assertEquals(self.cfg.pid_dir, DEFAULT_PID_DIR)
        self.assertIs(self.cfg.heartbeat_interval, None)
        self.cp.processCmd('heartbeat_interval 0')
        self.assertEquals(self.cfg.heartbeat_interval, 0)

    def test_readConfig(self):
        with closing(NamedTemporaryFile()) as tmpfile:
            tmpfile.write('heartbeat_interval 123\n')
            tmpfile.flush()
            self.cfg.readConfig(tmpfile.name)
        self.assertEquals(self.cfg.heartbeat_interval, 123)


class Test_events(Test_Config_Base):
    def test_heartbeat(self):
        self.assertFalse(self.cfg.heartbeatactive.isSet())
        self.cp.processCmd('heartbeat_interval 0')
        self.assertFalse(self.cfg.heartbeatactive.isSet())
        self.cp.processCmd('heartbeat_interval 1')
        self.assertTrue(self.cfg.heartbeatactive.isSet())

    def test_configuredevent(self):
        self.assertFalse(self.cfg.configuredevent.isSet())
        self.cfg.heartbeat_interval = 1
        self.cfg.data_port = 1
        self.cfg.antelope_orb_name = 1
        self.assertTrue(self.cfg.configuredevent.isSet())

    def test_dataserverconfigupdate(self):
        called = [False]
        def handler():
            self.cfg.dataserverconfigupdate.wait()
            called[0] = True
        self.assertFalse(self.cfg.dataserverconfigupdate.isSet())
        spawn(handler)
        sleep(0)
        self.cfg.antelope_orb_select = '.*'
        wait()
        self.assertTrue(called[0])


class Test_log_props(Test_Config_Base):
    def test_log_level(self):
        self.cfg.log_level = 'error'
        self.assertEquals(logging.getLogger().getEffectiveLevel(), logging.ERROR)
        self.cfg.log_level = 'warn'
        self.assertEquals(logging.getLogger().getEffectiveLevel(), logging.WARNING)
        self.cfg.log_level = 'foobar'
        self.assertEquals(self.cfg.log_level, 'warn')

    def test_log_config(self):
        self.cfg.log_config = 'logging.yaml'


if __name__ == '__main__':
    unittest.main()

