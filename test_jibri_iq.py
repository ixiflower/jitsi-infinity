#!/usr/bin/env python3
import socket, time, uuid, base64, sys

jid = "jibri@auth.meet.jitsi"
password = sys.argv[1] if len(sys.argv) > 1 else ""

if not password:
    print("Usage: test-jibri-iq.py <password>")
    sys.exit(1)

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)

def send(x):
    s.send(x.encode() if isinstance(x, str) else x)
    time.sleep(0.3)

def recv(t=3):
    s.settimeout(t)
    try:
        return s.recv(65536)
    except:
        return b""

send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1)
d = recv()
print(f"Stream: {len(d)}B")

auth = base64.b64encode(b"\x00jibri\x00" + password.encode()).decode()
send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth}</auth>")
time.sleep(1)
d = recv()
print(f"Auth: {d[:150]}")
if b"failure" in d:
    print("AUTH FAILED")
    s.close()
    sys.exit(1)

send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1)
recv()

sid = uuid.uuid4().hex[:8]
send(f"<iq type='set' id='bind-1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>test-{sid}</resource></bind></iq>")
time.sleep(1)
d = recv()
print(f"Bind: {d[:150]}")

send("<iq type='set' id='sess-1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(1)
recv()

iq = ("<iq type='set' to='focus@auth.meet.jitsi/focus' id='self-test-1'>"
      "<jibri xmlns='http://jitsi.org/protocol/jibri' action='start' "
      "room='selftest-vps@muc.meet.jitsi' recording_mode='file'/>"
      "</iq>")
print(f"Sending JibriIq ({len(iq)}B)...")
send(iq)
time.sleep(3)
d = recv()
print(f"Response ({len(d)}B): {d[:600]}")
s.close()
