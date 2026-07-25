#!/usr/bin/env python3
"""Quick XMPP test — connect, auth, join brewery, print response."""
import socket, ssl, base64, time, uuid, os

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)

def recv_until(marker, timeout=5):
    s.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    return data

s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>", 5)
print("1. Features OK")

s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
resp = s.recv(4096)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname="xmpp.meet.jitsi")
print("2. TLS OK")

s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>", 5)

pw = os.environ.get("JIBRI_XMPP_PASSWORD", "")
auth = b"\x00jibri\x00" + pw.encode()
s.send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{base64.b64encode(auth).decode()}</auth>".encode())
resp = recv_until(b"<success", 10)
if b"<success" in resp:
    print("3. AUTH OK")
else:
    print(f"3. AUTH FAILED: {resp[:200]}"); exit(1)

s.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
recv_until(b"</stream:features>", 5)

rid = str(uuid.uuid4())[:8]
s.send(f"<iq type='set' id='b1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>test-{rid}</resource></bind></iq>".encode())
time.sleep(0.5); s.recv(8192)
s.send(b"<iq type='set' id='s1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(0.5); s.recv(8192)

# Send presence to brewery
s.send(f"<presence to='jibribrewery@internal-muc.meet.jitsi/test-{rid}'><x xmlns='http://jabber.org/protocol/muc'/></presence>".encode())
time.sleep(3)
data = b""
s.settimeout(3)
try:
    while True:
        data += s.recv(8192)
except:
    pass
print(f"4. MUC response: {len(data)}b")
if data:
    print(f"   Contains 'error': {b'error' in data}")
    print(f"   Contains 'presence': {b'presence' in data}")
    if b"error" in data:
        print(f"   Preview: {data[:300]}")
    elif b"presence" in data:
        print(f"   ACCEPTED! First 200b: {data[:200]}")

s.send(b"</stream:stream>")
s.close()
