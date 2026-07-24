#!/usr/bin/env python3
"""Debug: check what comes back after STARTTLS."""
import socket

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)
s.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
raw = b""
while True:
    try:
        c = s.recv(4096)
        if not c:
            break
        raw += c
        # Check for features end
        if b"</stream:features>" in raw:
            print(f"FEATURES ({len(raw)} bytes):")
            print(raw.decode("utf-8", errors="replace"))
            break
    except:
        break

# Now send STARTTLS
s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
raw2 = b""
while True:
    try:
        c = s.recv(4096)
        if not c:
            break
        raw2 += c
        print(f"AFTER STARTTLS got {len(raw2)} bytes: {raw2[:200]}")
        if b"</proceed>" in raw2 or b"</failure>" in raw2:
            print(f"COMPLETE: {raw2.decode('utf-8', errors='replace')}")
            break
    except socket.timeout:
        print(f"TIMEOUT after {len(raw2)} bytes: {raw2[:200]}")
        break

s.close()
