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
    # accepted traffic
    pkt1 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt1 = pkt1 /IP(dst=addr) / TCP(dport=1235, sport=1234) / sys.argv[2]
    # denied traffic
    pkt2 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt2 = pkt2 /IP(dst=addr) / TCP(dport=1237, sport=1236) / sys.argv[2]
    # background traffic
    pkt3 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt3 = pkt3 /IP(dst='10.0.1.11') / UDP(dport=1239, sport=1238) / sys.argv[2]
    # background traffic
    pkt4 =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt4 = pkt4 /IP(dst='10.0.1.12') / UDP(dport=1231, sport=1230) / sys.argv[2]
    # pkt.show2()
    while True:
        sendp(pkt4, iface=iface, verbose=False)
        sendp(pkt3, iface=iface, verbose=False)
        sendp(pkt4, iface=iface, verbose=False)
        sendp(pkt1, iface=iface, verbose=False)
        sendp(pkt4, iface=iface, verbose=False)
        sendp(pkt3, iface=iface, verbose=False)

if __name__ == '__main__':
    main()
