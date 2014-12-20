#!/usr/bin/env python

import gevent

from orbpktsrc import OrbPktSrc

s = OrbPktSrc('anfexport:prelim:', '.*', '', transformation=lambda x: (x.srcname))
s.start()

def clock():
    while True:
        print 'tick'
        gevent.sleep(0.25)


def subscriber():
    print 'Subscribing'
    with s.subscription() as q:
        for n in xrange(3):
            print repr(q.get())[:75]
    print 'Cancelled subscription'

gevent.spawn(clock)
gevent.spawn(subscriber)
gevent.wait()

