#!/usr/bin/env python3
"""Quick test — print XMPP stream features from Prosody."""
import socket

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=5)
s.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
data = b""
while b"</stream:features>" not in data:
    data += s.recv(4096)
print(data.decode("utf-8", errors="replace"))
s.close()
