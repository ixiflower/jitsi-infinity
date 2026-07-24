#!/usr/bin/env python3
"""Debug: check SASL mechanisms after TLS."""
import socket, ssl

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)
s.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
raw = b""
while b"</stream:features>" not in raw:
    raw += s.recv(4096)

s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
raw = s.recv(4096)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname="xmpp.meet.jitsi")

s.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
raw = b""
while b"</stream:features>" not in raw:
    raw += s.recv(4096)
print("POST-TLS FEATURES:")
print(raw.decode("utf-8", errors="replace"))
s.close()
