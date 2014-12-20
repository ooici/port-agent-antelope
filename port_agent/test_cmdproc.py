#!/usr/bin/env python

import unittest

import mock

from cmdproc import (CmdProcessor, CmdParseError, ValueConversionError,
                     CmdUsageError, UnknownCmd)


class Test_CmdProcessor(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()

    def test_setCmd(self):
        self.cp.setCmd('cmd', None, None)

    def test_parseCmd(self):
        r = self.cp._parseCmd('foo')
        self.assertEquals(r, ('foo', None))

    def test_parseCmd_w_arg(self):
        r = self.cp._parseCmd('foo bar')
        self.assertEquals(r, ('foo', 'bar'))

    def test_parseCmd_w_2_args(self):
        self.assertRaises(CmdParseError, self.cp._parseCmd, 'foo bar baz')

    def test_parseCmd_blank(self):
        self.assertRaises(CmdParseError, self.cp._parseCmd, '')

    def test_processCmd(self):
        sentinel = []
        outerval = '123'
        def cb(innerval, *args, **kwargs):
            self.assertEquals(innerval, 123)
            self.assertEquals(args, ('astr', 'bstr'))
            self.assertEquals(kwargs, dict(foo='bar', sna='foo'))
            sentinel.append(0)
        self.cp.setCmd('cmd', int, cb, 'astr', foo='bar')
        self.cp.processCmd('cmd 123', 'bstr', sna='foo')
        self.assertEquals(sentinel, [0])

    def test_processCmd_bad_value(self):
        def cb(*args, **kwargs):
            pass
        self.cp.setCmd('cmd', int, cb)
        self.assertRaises(ValueConversionError, self.cp.processCmd, 'cmd hello')

    def test_processCmd_bad_args(self):
        def cb(*args, **kwargs):
            pass
        self.cp.setCmd('cmd', None, cb)
        self.assertRaises(CmdUsageError, self.cp.processCmd, 'cmd hello')

    def test_processCmd_unknown(self):
        self.assertRaises(UnknownCmd, self.cp.processCmd, 'foobar')

    def test_processCmds(self):
        sent = []
        def cb(*args, **kwargs):
            sent.append(True)
        self.cp.setCmd('cmd', None, cb)
        self.cp.processCmds('cmd\ncmd')
        self.assertEquals(sent, [True, True])

    def test_processCmds2(self):
        sent = []
        def cb(*args, **kwargs):
            sent.append(True)
        def cb2(val, *args, **kwargs):
            sent.append(True)
        self.cp.setCmd('cmd', None, cb)
        self.cp.setCmd('cmd2', int, cb)
        self.cp.processCmds('cmd\ncmd2 123')
        self.assertEquals(sent, [True, True])

    def test_processCmds_blank(self):
        self.cp.processCmds('')

if __name__ == '__main__':
    unittest.main()

