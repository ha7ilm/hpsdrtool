#!/usr/bin/python2
from socket import *
import sys, time, signal, struct

try: rxip=sys.argv[1]
except:
    print sys.argv[0]+" <hpsdr_metis_ip>"
    sys.exit(1)
rxipparts=rxip.split(".")
bcastip=".".join(rxipparts[0:3]+["255",])
localips=[ip for ip in gethostbyname_ex(gethostname())[2] if not ip.startswith("127.")][:1]

s=socket(AF_INET, SOCK_DGRAM)
s.bind(('', 1024))
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

def sighandler(signum, frame):
    stop()
    sys.exit(0)
signal.signal(signal.SIGTERM, sighandler)

use_preamp="--preamp" in sys.argv
if use_preamp: print "preamp on"
freq=7e6
if "--freq" in sys.argv: freq=int(sys.argv[sys.argv.index("--freq")+1])
print "center frequency:", freq


def bcast():
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    s.sendto("\xef\xfe\x02"+("\x00"*60), (bcastip, 1024))
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 0)
    s.settimeout(0.1)
    starttime=time.time()
    while time.time()-starttime<0.5:
        try: rx=s.recvfrom(1024)
        except: continue
        ip=rx[1][0]
        payload=rx[0]
        if ip in localips: print "local bcastmsg loopback, skip"
        else:
            if ip==rxip and payload.startswith("\xef\xfe"): return True
    return False

def start(): s.sendto("\xef\xfe\x04\x01"+("\x00"*60), (rxip, 1024))
def stop(): s.sendto("\xef\xfe\x04\x00"+("\x00"*60), (rxip, 1024))

def cmd(freq, preamp):
    freqdata=struct.pack(">I",freq)
    c3=0x18+(4 if preamp else 0)
    d="\xef\xfe\x01\x02\x00\x00\x00\x09\x7f\x7f\x7f\x00\xda\x00"+chr(c3)+"\x80"+("\x00"*504)+"\x7f\x7f\x7f\x04"+freqdata+("\x00"*504)
    s.sendto(d, (rxip, 1024))

def procpkt(d):
    print len(d)

def rxpkt():
    try: rxdata=s.recvfrom(2048)
    except: return
    d=rxdata[0]
    print len(d)
    if not d[0:2]=="\xef\xfe":
        print "pkt header does not match"
        return
    if not ord(d[2])==1:
        print "pkt signature does not match"
        return
    if not ord(d[3])==6:
        print "pkt ep does not match"
        return
    seqnum=ord(d[7])+(ord(d[6])<<8)+(ord(d[5])<<16)+(ord(d[4])<<24)
    procpkt(d[8:512+8])
    procpkt(d[512+8:])
    print "seqnum", seqnum

if not bcast():
    print "receiver not found"
    sys.exit(1)
print "receiver found"
start()
while True: rxpkt()
