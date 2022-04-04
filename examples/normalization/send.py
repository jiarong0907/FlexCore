#!/usr/bin/env python
import argparse
import sys
import socket
import random
import struct

from scapy.all import sendp, send, get_if_list, get_if_hwaddr
from scapy.all import Packet
from scapy.all import Ether, IP, UDP, TCP

def get_if():
    ifs=get_if_list()
    iface=None # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print "Cannot find eth0 interface"
        exit(1)
    return iface

def main():

    if len(sys.argv)<3:
        print 'pass 2 arguments: <destination> "<message>"'
        exit(1)

    addr = socket.gethostbyname(sys.argv[1])
    iface = get_if()

    # print "sending on interface %s to %s" % (iface, str(addr))
    # normal traffic
    pkt1 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt1 = pkt1 /IP(dst=addr) / TCP(dport=1234, sport=1235) / sys.argv[2]
    # IDS evasion traffic
    pkt2 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt2 = pkt2 /IP(dst=addr, ttl=2) / TCP(dport=1234, sport=1236) / sys.argv[2]
    # Covert channel traffic
    pkt3 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt3 = pkt3 /IP(dst=addr, tos=3) / TCP(dport=1234, sport=1237) / sys.argv[2]
    # pkt.show2()
    while True:
        if addr == "10.0.1.255":
            sendp(pkt1, iface=iface, verbose=False)
            sendp(pkt2, iface=iface, verbose=False)
            sendp(pkt1, iface=iface, verbose=False)
            sendp(pkt2, iface=iface, verbose=False)
            sendp(pkt1, iface=iface, verbose=False)
        else:
            sendp(pkt1, iface=iface, verbose=False)
            sendp(pkt1, iface=iface, verbose=False)
            sendp(pkt3, iface=iface, verbose=False)
            sendp(pkt1, iface=iface, verbose=False)
            sendp(pkt1, iface=iface, verbose=False)

if __name__ == '__main__':
    main()
