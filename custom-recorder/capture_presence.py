#!/usr/bin/env python3
"""Capture the EXACT Jibri-1 presence stanza from the brewery MUC."""
import socket, ssl, base64, time, uuid, os

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)
def recv_until(marker, timeout=5):
    s.settimeout(timeout); data = b""
    while marker not in data:
        c = s.recv(4096)
        if not c: break
        data += c
    return data

s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>")
s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
s.recv(4096)
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname="xmpp.meet.jitsi")
s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>")
pw = os.environ.get("JIBRI_XMPP_PASSWORD", "")
auth = b"\x00jibri\x00" + pw.encode()
s.send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{base64.b64encode(auth).decode()}</auth>".encode())
resp = recv_until(b"<success", 10)
s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>")
rid = str(uuid.uuid4())[:8]
s.send(f"<iq id='b1' type='set'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>cap-{rid}</resource></bind></iq>".encode())
time.sleep(0.5); s.recv(8192)
s.send(b"<iq id='s1' type='set'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(0.5); s.recv(8192)

# Join brewery
s.send(f"<presence to='jibribrewery@internal-muc.meet.jitsi/cap-{rid}'><x xmlns='http://jabber.org/protocol/muc'/></presence>".encode())
time.sleep(3)
data = b""
s.settimeout(3)
try:
    while True:
        d = s.recv(32768)
        if not d: break
        data += d
except: pass

# Print all presence stanzas from other occupants
stanzas = data.split(b"</presence>")
for i, st in enumerate(stanzas):
    if b"jibri-status" in st or b"busy-status" in st:
        idx = st.find(b"<presence")
        if idx >= 0:
            print(f"\n=== Jibri Presence {i} ===")
            print(st[idx:].decode("utf-8", errors="replace")[:2000])

s.send(b"</stream:stream>")
s.close()
