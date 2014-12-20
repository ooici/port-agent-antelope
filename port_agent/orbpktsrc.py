#!/usr/bin/env python
"""
Gevent based orb packet publisher.

Correct use of this module requires the `ANTELOPE_PYTHON_GILRELEASE`
environment variable to be set, to signal the Antelope Python bindings to
release the GIL when entering Antelope C functions. E.g.

    export ANTELOPE_PYTHON_GILRELEASE=1

"""

from contextlib import contextmanager
from cPickle import dumps
import os
from weakref import proxy

from gevent import Greenlet
from gevent.threadpool import ThreadPool, wrap_errors
from gevent.queue import Queue, Empty, Full

from antelope.brttpkt import OrbreapThr, Timeout, NoData
from antelope.Pkt import Packet

from ooi.logging import log

import ntp


class GilReleaseNotSetError(Exception): pass


if 'ANTELOPE_PYTHON_GILRELEASE' not in os.environ:
    raise GilReleaseNotSetError("ANTELOPE_PYTHON_GILRELEASE not in environment")

MAX_QUEUE_SIZE = 1000

class OrbPktSrc(Greenlet):
    """Gevent based orb packet publisher.

    :param transformation: Optional transformation function
    :type transformation: `func`

    Gets packets from an orbreap thread in a non-blocking fashion using the
    gevent threadpool functionality, and publishes them to subscribers.

    The transformation function should take a single argument, the unstuffed Packet
    object. It's return value is placed into the queue.

    Transformation function example::

        from pickle import dumps

        def transform(packet):
            return dumps(packet)

    """
    def __init__(self, srcname, select=None, reject=None, transformation=None, after=-1):
        Greenlet.__init__(self)
        self.srcname = srcname
        self.select = select
        self.reject = reject
        self.after = after
        self._queues = set()
        self.transformation = transformation

    def _run(self):
        try:
            args = self.srcname, self.select, self.reject
            # TODO Review this queue size
            # TODO Review reasoning behind using OrbreapThr vs. normal ORB API
            # I think it had something to do with orb.reap() blocking forever
            # on comms failures; maybe we could create our own orbreapthr
            # implementation?
            with OrbreapThr(*args, timeout=1, queuesize=10000) as orbreapthr:
                log.info("Connected to ORB %s %s %s" % (self.srcname, self.select,
                                                        self.reject, self.after))
                threadpool = ThreadPool(maxsize=1)
                try:
                    while True:
                        try:
                            success, value = threadpool.spawn(
                                    wrap_errors, (Exception,), orbreapthr.get, [], {}).get()
                            timestamp = ntp.now()
                            if not success:
                                raise value
                        except (Timeout, NoData), e:
                            log.debug("orbreapthr.get exception %r" % type(e))
                            pass
                        else:
                            if value is None:
                                raise Exception('Nothing to publish')
                            self._publish(value, timestamp)
                finally:
                    # This blocks until all threads in the pool return. That's
                    # critical; if the orbreapthr dies before the get thread,
                    # segfaults ensue.
                    threadpool.kill()
        except Exception, e:
            log.error("OrbPktSrc terminating due to exception", exc_info=True)
            raise
        finally:
            log.info("Disconnected from ORB %s %s %s" % (self.srcname, self.select,
                                                         self.reject))

    def _publish(self, r, timestamp):
        pktid, srcname, orbtimestamp, raw_packet = r
        packet = Packet(srcname, orbtimestamp, raw_packet)
        if self.transformation is not None:
            packet = self.transformation(packet)
        for queue in self._queues:
            try:
                queue.put((packet, timestamp), block=False)
            except Full:
                log.debug("queue overflow")

    @contextmanager
    def subscription(self):
        """This context manager returns a Queue object from which the
        subscriber can get pickled orb packets.

        The returned object is actually a weakref proxy to the real Queue. This
        ensures that the real Queue is destroyed as soon as the context exits,
        as nobody but the context manager has the real reference.

        Example::

            with orbpktsrc.subscription() as queue:
                while True:
                    pickledpacket = queue.get()
                    ...
        """
        queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self._queues.add(queue)
        try:
            yield proxy(queue)
        finally:
            # Stop publishing
            self._queues.remove(queue)

