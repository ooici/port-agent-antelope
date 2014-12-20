#!/usr/bin/env python

# TODO Maybe config updates should emit events?
# Maybe commands should emit events too, and config updates just listen to
# those and or chain them somehow? what about gevent's link thing?

from functools import partial
import logging

from gevent.event import Event

from ooi.logging import log
import ooi.logging


DEFAULT_PID_DIR = "/var/ooici/port_agent/pid"
DEFAULT_LOG_LEVEL = 'warn'


class Config(object):
    cmds = {
        'heartbeat_interval': (int, None),
        'command_port': (int, None),
        'data_port': (int, None),
        'pid_dir': (str, DEFAULT_PID_DIR),
        'log_level': (str, DEFAULT_LOG_LEVEL),
        'log_config': (str, None),
        'antelope_orb_name': (str, None),
        'antelope_orb_select': (str, None),
        'antelope_orb_reject': (str, None),
        'antelope_orb_after': (float, -1),
    }

    # TODO: What about command_port?
    CONFIG_DEPS = set([
        'heartbeat_interval',
        'data_port',
        'antelope_orb_name',
    ])

    # When one of these changes, it signals the data server to restart
    DATASERVER_DEPS = [
        'data_port',
        'antelope_orb_name',
        'antelope_orb_select',
        'antelope_orb_reject',
        'antelope_orb_after',
    ]

    def setval(self, name, val, *args, **kwargs):
            setattr(self, name, val)

    def __init__(self, options, cmdproc):
        self.configuredevent = Event()
        self.dataserverconfigupdate = Event()
        self.heartbeatactive = Event()
        for name, (converter, default) in self.cmds.iteritems():
            self.cmdproc = cmdproc
            # Initialize attr with default val
            setattr(self, name, default)
            # Create command to set attr
            # cmdserver sends sock after val; will that mess this up?
            setval = partial(self.setval, name)
            cmdproc.setCmd(name, converter, setval)

        # Set a default loglevel?
        # update from config file
        if hasattr(options, 'conffile') and options.conffile is not None:
            self.readConfig(options.conffile)
        # update from command line
        if hasattr(options, 'verbose') and options.verbose is True:
            self.log_level = 'debug'
        if hasattr(options, 'command_port') and options.command_port is not None:
            self.command_port = options.command_port

    def readConfig(self, conffile):
        with open(conffile, 'rU') as file:
            for line in file:
                self.cmdproc.processCmd(line)

    def __setattr__(self, name, value):
        super(Config, self).__setattr__(name, value)
        if not self.configuredevent.isSet():
            configured_attrs = set()
            for attr in self.CONFIG_DEPS:
                if hasattr(self, attr) and getattr(self, attr) is not None:
                    configured_attrs.add(attr)
            if configured_attrs == self.CONFIG_DEPS:
                self.configuredevent.set()
        if name in self.DATASERVER_DEPS:
            self.dataserverconfigupdate.set()
            self.dataserverconfigupdate.clear()

    @property
    def heartbeat_interval(self):
        return self._heartbeat_interval

    @heartbeat_interval.setter
    def heartbeat_interval(self, value):
        self._heartbeat_interval = value
        if value > 0:
            self.heartbeatactive.set()
        else:
            self.heartbeatactive.clear()

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, val):
        levels = {
                    'error': logging.ERROR,
                    'warn': logging.WARNING,
                    'info': logging.INFO,
                    'debug': logging.DEBUG,
                    'mesg': logging.DEBUG,
                }
        try:
            level = levels[val]
        except KeyError:
            log.error("Unknown logging level %s" % val)
        else:
            self._log_level = val
            logging.getLogger().setLevel(level)

    @property
    def log_config(self):
        return self._log_config

    @log_config.setter
    def log_config(self, val):
        try:
            ooi.logging.config.add_configuration(val)
            self._log_config = val
        except Exception:
            log.error("Failed to read log config '%s'" % val, exc_info=True)

