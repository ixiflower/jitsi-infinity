#!/usr/bin/env python3
import socket, time, uuid, base64, ssl, sys

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
    try: return s.recv(65536)
    except: return b""

# Open stream
send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1)
d = recv()
print(f"Stream: {len(d)}B")

# STARTTLS
if b"starttls" in d:
    print("STARTTLS...")
    send("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    time.sleep(1)
    d = recv()
    if b"proceed" in d:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(s, server_hostname="xmpp.meet.jitsi")
        print("TLS OK")
        send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        time.sleep(1)
        recv()
    else:
        print("TLS failed:", d[:200])
        s.close()
        exit(1)

# Auth
auth = base64.b64encode(b"\x00jibri\x00" + password.encode()).decode()
send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth}</auth>")
time.sleep(1)
d = recv()
print(f"Auth: {d[:200]}")
if b"failure" in d:
    print("AUTH FAILED")
    s.close()
    exit(1)

# Re-stream
send("<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
time.sleep(1)
recv()

# Bind
sid = uuid.uuid4().hex[:8]
send(f"<iq type='set' id='bind-1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>test-{sid}</resource></bind></iq>")
time.sleep(1)
d = recv()
print(f"Bind: {d[:200]}")

# Session
send("<iq type='set' id='sess-1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(1)
recv()

# Join the room's MUC first (JibriIq needs room context)
room = "selftest-vps"
room_muc = f"{room}@muc.meet.jitsi"
send(f"<presence to='{room_muc}/{sid}'><x xmlns='http://jabber.org/protocol/muc'/></presence>")
time.sleep(2)
recv()
print(f"Joined MUC: {room_muc}")

# Send JibriIq START to Jicofo
iq = (f"<iq type='set' to='focus@auth.meet.jitsi/focus' id='self-test-1'>"
      f"<jibri xmlns='http://jitsi.org/protocol/jibri' action='start' "
      f"room='{room_muc}' recording_mode='file'/>"
      f"</iq>")
print(f"Sending JibriIq ({len(iq)}B)...")
send(iq)
time.sleep(3)
d = recv()
print(f"Response ({len(d)}B): {d[:600]}")
s.close()
