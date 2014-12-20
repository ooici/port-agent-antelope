#!/usr/bin/env python

from functools import partial
from optparse import OptionParser
import sys
import os
import signal

from daemon import DaemonContext

from lockfile import LockFailed
from lockfile.pidlockfile import PIDLockFile

from cmdproc import CmdProcessor, UnknownCmd
from version import __version__


BASE_FILENAME = 'port_agent'
DEFAULT_PID_DIR = "/var/ooici/port_agent/pid"

def get_pidfile(options):
    filename = "%s_%s.pid" % (BASE_FILENAME, options.command_port)
    path = os.path.join(options.pid_dir, filename)
    return path


def start_port_agent(options):
    # DO NOT IMPORT THESE BEFORE ENTERING CONTEXT
    import gevent
    from config import Config
    from port_agent import PortAgent
    from ooi.logging import config, log
# This is a problem
# 1. Where should it get installed?
# 2. Should it be a resource?
# 3. How to configured where to read it from?
# 4. Add new cmd to set it?
#    config.add_configuration('logging.yaml')
    log.info("Starting")
    # get a fresh cmdproc
    cmdproc = CmdProcessor()
    cfg = Config(options, cmdproc)
    agent = PortAgent(cfg, cmdproc)
    gevent.signal(signal.SIGTERM, agent.kill)
    gevent.signal(signal.SIGINT, agent.kill)
    agent.start()
    agent.join()
    if not agent.successful():
        log.critical("EXIT_FAILURE")
        return 1
    return 0

def send_commands(options):
    import socket
    from packet import makepacket, PacketType, HEADER_SIZE, ReceivedPacket
    import ntp
    sock = socket.create_connection((options.host, options.command_port), 10)
    cmdstr = '\n'.join(options.command)
    pkt = makepacket(PacketType.PORT_AGENT_COMMAND, ntp.now(), cmdstr)
    sock.sendall(pkt)
    headerbuf = bytearray()
    while len(headerbuf) < HEADER_SIZE:
        bytes = sock.recv(HEADER_SIZE - len(headerbuf))
        if len(bytes) == 0: raise Exception("Peer disconnected")
        headerbuf.extend(bytes)
    pkt = ReceivedPacket(headerbuf)
    databuf = bytearray()
    datasize = pkt.datasize
    while len(databuf) < datasize:
        bytes = sock.recv(datasize - len(databuf))
        if len(bytes) == 0: raise Exception("Peer disconnected")
        databuf.extend(bytes)
    pkt.validate(databuf)
    print 'RX Packet: ', pkt


def main(args=None):
    if args is None:
        args = sys.argv
    op = OptionParser(version=__version__)
    op.add_option("-c", "--conffile", action="store",
                    help='Path to port_agent config file.')
    op.add_option("-v", "--verbose", action="store_true",
                    help='Set loglevel to debug.')
    op.add_option("-k", "--kill", action="store_true",
                    help='Kill a daemon processes associated to a command port.')
    op.add_option("-s", "--single", action="store_true",
                    help='Run in foreground; do not daemonize.')
# Bill French says we don't need this.
#    op.add_option("-y", "--ppid", action="store", type='int',
#                    help='Poison pill, if parent process is gone then shutdown')
    op.add_option("-i", "--identity", action="store",
                help='identifiction for the port agent process. Ignored in the port agent process.')
    op.add_option("-p", "--command_port", action="store", type='int',
                    help='Observatory command port number. Required here or in conffile.')
    op.add_option("-C", "--command", action="append",
                    help='Send command to remote port agent and exit. May be specified multiple times.')
    op.add_option("-H", "--host", action="store", default='localhost',
                    help='Host to command. Only significant with -C option. Defaults to localhost.')
    (options, args) = op.parse_args(args[1:])

    # We can't import the config module until AFTER we enter the daemon
    # context, so we can't use it to get the command_port and pid_dir
    # parameters from the config file, which we need to determine the path to
    # the PID file.
    options.pid_dir = DEFAULT_PID_DIR
    if options.conffile:
        cmdproc = CmdProcessor()
        if not options.command_port:
            cmdproc.setCmd('command_port', int, partial(setattr, options, 'command_port'))
        cmdproc.setCmd('pid_dir', str, partial(setattr, options, 'pid_dir'))
        with open(options.conffile) as f:
            for line in f:
                try: cmdproc.processCmd(line)
                except UnknownCmd: pass
    if not options.command_port:
        print "Must specify command_port on command line or in conffile"
        return 1

    if options.command:
        send_commands(options)
        return 0

    if options.kill:
        with open(get_pidfile(options)) as f:
            pid = int(f.read().strip())
        print "sending SIGINT to pid %d" % pid
        os.kill(pid, signal.SIGTERM)
        return 0

    context = DaemonContext(
        pidfile = PIDLockFile(get_pidfile(options)),
        working_directory = os.getcwd(),
    )

    if options.single:
        context.detach_process = False
        context.stdout = sys.stdout
        context.stderr = sys.stderr

    try:
        with context:
            return start_port_agent(options)
    except LockFailed:
        print "Failed to lock PID file %r" % get_pidfile(options)
        return 1

    raise Exception("This should be unreachable")
