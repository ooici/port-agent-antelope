#!/usr/bin/env python

def orbpkt2dict(orbpkt):
    d = dict()
    channels = []
    d['channels'] = channels
    for orbchan in orbpkt.channels:
        channel = dict()
        channels.append(channel)
        channel['calib'] = orbchan.calib
        channel['calper'] = orbchan.calper
        channel['chan'] = orbchan.chan
        channel['cuser1'] = orbchan.cuser1
        channel['cuser2'] = orbchan.cuser2
        channel['data'] = orbchan.data
        channel['duser1'] = orbchan.duser1
        channel['duser2'] = orbchan.duser2
        channel['iuser1'] = orbchan.iuser1
        channel['iuser2'] = orbchan.iuser2
        channel['iuser3'] = orbchan.iuser3
        channel['loc'] = orbchan.loc
        channel['net'] = orbchan.net
        channel['nsamp'] = orbchan.nsamp
        channel['samprate'] = orbchan.samprate
        channel['segtype'] = orbchan.segtype
        channel['sta'] = orbchan.sta
        channel['time'] = orbchan.time
    d['db'] = orbpkt.db
    d['dfile'] = orbpkt.dfile
    d['pf'] = orbpkt.pf.pf2dict()
    srcname = orbpkt.srcname
    d['srcname'] = dict(
                        net=srcname.net,
                        sta=srcname.sta,
                        chan=srcname.chan,
                        loc=srcname.loc,
                        suffix=srcname.suffix,
                        subcode=srcname.subcode,
                        joined=srcname.join()
                       )
    d['string'] = orbpkt.string
    d['time'] = orbpkt.time
    pkttype = orbpkt.type
    d['type'] = dict(
                        content=pkttype.content,
                        name=pkttype.name,
                        suffix=pkttype.suffix,
                        hdrcode=pkttype.hdrcode,
                        bodycode=pkttype.bodycode,
                        desc=pkttype.desc,
                    ),
    d['version'] = orbpkt.version

    return d

