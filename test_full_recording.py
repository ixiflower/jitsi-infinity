#!/usr/bin/env python3
"""Full recording test - join a room and trigger recording."""
import socket, time, uuid, base64, ssl, sys

password = sys.argv[1]
host = "xmpp.meet.jitsi"

s = socket.create_connection((host, 5222), timeout=10)

def send(x):
    if isinstance(x, str): x = x.encode()
    s.send(x)
    time.sleep(0.3)

def recv(t=3):
    s.settimeout(t)
    try: return s.recv(65536)
    except: return b""

# TLS
send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1); recv()
send("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
time.sleep(1); recv()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname=host)

send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1); recv()

# Auth as jibri user
auth = base64.b64encode(b"\x00jibri\x00" + password.encode()).decode()
send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth}</auth>")
time.sleep(1)
d = recv()
print(f"Auth: {d[:200]}")
if b"failure" in d:
    print("AUTH FAILED"); s.close(); sys.exit(1)

send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1); recv()

sid = uuid.uuid4().hex[:8]
send(f"<iq type='set' id='b1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>test-{sid}</resource></bind></iq>")
time.sleep(1)
d = recv(); print(f"Bind: {d[:200]}")

send("<iq type='set' id='s1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(0.5); recv()

# Join room
room = f"autotest-{uuid.uuid4().hex[:4]}"
room_jid = f"{room}@muc.meet.jitsi"
print(f"\nJoining room: {room_jid}")
send(f"<presence to='{room_jid}/{sid}'><x xmlns='http://jabber.org/protocol/muc'/></presence>")
time.sleep(3)
d = recv()
print(f"Room response ({len(d)}B): {d[:300]}")

time.sleep(2)

# Send JibriIq
iq = (f"<iq type='set' to='focus@auth.meet.jitsi/focus' id='start-1'>"
      f"<jibri xmlns='http://jitsi.org/protocol/jibri' action='start' "
      f"room='{room_jid}' recording_mode='file'/>"
      f"</iq>")
print(f"\nSending JibriIq...")
send(iq)
time.sleep(4)
d = recv()
print(f"Response: {d[:500]}")
s.close()
