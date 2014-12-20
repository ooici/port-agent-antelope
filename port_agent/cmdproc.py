#!/usr/bin/env python

from ooi.logging import log

class CmdProcError(Exception): pass

class CmdParseError(CmdProcError):
    """Raised when the command string cannot be parsed."""
    pass

class ValueConversionError(CmdProcError):
    """Raised when a value string cannot be converted by the specified
    conversion function."""
    pass

class CmdUsageError(CmdProcError):
    """Raised when an argument is passed to a command which does not accept an
    argument."""
    pass

class UnknownCmd(CmdProcError):
    pass

class CmdProcessor(object):
    def __init__(self):
        self.cmds = {}

    def setCmd(self, name, converter, callback, *args, **kwargs):
        self.cmds[name] = converter, callback, args, kwargs

    def _parseCmd(self, cmdstr):
        val = None
        parts = cmdstr.split()
        try:
            name = parts[0]
        except IndexError:
            raise CmdParseError(cmdstr)
        if len(parts) == 2:
            val = parts[1]
        elif len(parts) > 2:
            raise CmdParseError(cmdstr)
        return name, val

    def _executeCmd(self, name, val, *args, **kwargs):
        log.info("Executing command %s %s" % (name, val))
        try:
            converter, callback, cbargs, cbkwargs = self.cmds[name]
        except KeyError:
            raise UnknownCmd(name)
        if converter is not None:
            try:
                val = converter(val)
            except Exception, e:
                raise ValueConversionError(val, e)
        elif val is not None:
            raise CmdUsageError(name)
        cbargs = list(cbargs)
        cbargs.extend(args)
        kwargs.update(cbkwargs)
        callback(val, *cbargs, **kwargs)

    def processCmd(self, cmdstr, *args, **kwargs):
        name, val = self._parseCmd(cmdstr)
        self._executeCmd(name, val, *args, **kwargs)

    def processCmds(self, cmdsstr, *args, **kwargs):
        for cmdstr in cmdsstr.strip().split('\n'):
            if cmdstr == '':
                continue
            try:
                self.processCmd(cmdstr, *args, **kwargs)
            except CmdProcError, e:
                log.error("Error processing command: %s" % e)

