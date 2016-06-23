"""
This file is part of Hpsdrtool.
Copyright (c) 2016 by Andras Retzler <randras@sdr.hu>

Hpsdrtool is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Hpsdrtool is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Hpsdrtool.  If not, see <http://www.gnu.org/licenses/>.
"""

#!/usr/bin/python2

from socket import *
import sys, time, signal, struct

def sighandler():
    if s: stop()
    sys.exit(0)

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
        if ip in localips: sys.stderr.write("local bcastmsg loopback, skip\n")
        else:
            if ip==rxip and payload.startswith("\xef\xfe"): return True
    return False

def start(): s.sendto("\xef\xfe\x04\x01"+("\x00"*60), (rxip, 1024))
def stop(): s.sendto("\xef\xfe\x04\x00"+("\x00"*60), (rxip, 1024))

def cmd(freq, preamp, rx):
    freqdata=struct.pack(">I",freq)
    rxbyte=chr(4 if rx else 2)
    c3=0x18+(4 if preamp else 0)
    #stock data from powersdr sniffing: 7f 7f 7f 00 5a 00 00 88; 7f 7f 7f 02 01 56 c8 01 (around 22 MHz)
    d="\xef\xfe\x01\x02\x00\x00\x00\x09\x7f\x7f\x7f\x00\xda\x00"+chr(c3)+"\x80"+("\x00"*504)+"\x7f\x7f\x7f"+rxbyte+freqdata+("\x00"*504)
    s.sendto(d, (rxip, 1024))

def procpkt(d):
    if no_iq_output:
        sys.stderr.write("pkt to decode: %d bytes\n"%len(d))
        return
    for i in range(8,len(d),8):
        sys.stdout.write(d[i:i+6])
        #if len(d[i:i+6])!=6: sys.stderr.write("pktlenerr: %d  "%len(d[i:i+6]))

def rxpkt():
    try: rxdata=s.recvfrom(2048)
    except: return
    d=rxdata[0]
    #sys.stderr.write(len(d\n))
    if not d[0:2]=="\xef\xfe":
        sys.stderr.write("pkt header does not match\n")
        return
    if not ord(d[2])==1:
        sys.stderr.write("pkt signature does not match\n")
        return
    if not ord(d[3])==6:
        sys.stderr.write("pkt ep does not match\n")
        return
    if not len(d)==1024+8:
        sys.stderr.write("pkt len does not match\n")
        return

    seqnum=ord(d[7])+(ord(d[6])<<8)+(ord(d[5])<<16)+(ord(d[4])<<24)
    procpkt(d[8:512+8])
    procpkt(d[512+8:])
    if no_iq_output: sys.stderr.write("seqnum: %d\n"%seqnum)

def main():
    global bcastip, s, localips, rxip, no_iq_output

    s=None

    try: rxip=sys.argv[1]
    except:
        sys.stderr.write("hpsdrtool <hpsdr_metis_ip> [--freq <freq_in_hz>] [--preamp] [--no-iq-output]\n")
        return 1

    rxipparts=rxip.split(".")
    bcastip=".".join(rxipparts[0:3]+["255",])
    localips=[ip for ip in gethostbyname_ex(gethostname())[2] if not ip.startswith("127.")][:1]
    no_iq_output = ("--no-iq-output" in sys.argv)

    s=socket(AF_INET, SOCK_DGRAM)
    s.bind(('', 1024))
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    signal.signal(signal.SIGTERM, sighandler)

    if not bcast():
        sys.stderr.write("receiver not found\n")
        return 1
    sys.stderr.write("receiver found\n")

    use_preamp="--preamp" in sys.argv
    if use_preamp: sys.stderr.write("preamp on\n")
    freq=7e6
    if "--freq" in sys.argv: freq=int(sys.argv[sys.argv.index("--freq")+1])
    sys.stderr.write("center frequency: %d\n"%int(freq))

    cmd(freq, use_preamp, 0)
    cmd(freq, use_preamp, 1)
    start()
    while True: rxpkt()

try: sys.exit(main())
except (KeyboardInterrupt, SystemExit): sighandler()
