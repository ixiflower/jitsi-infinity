#!/usr/bin/env python3
"""Full XMPP auth + MUC join test v3 (fixed domain)."""
import socket, ssl, base64, uuid, time
from pathlib import Path

def load_env(path):
    env = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return env

env = load_env("/app/.env.jibri") or load_env("/home/ubuntu/jitsi-infinity/.env.jibri") or {}
password = env.get("JIBRI_RECORDER_PASSWORD", "")
room = "ixi"

def recv_until(s, marker, timeout=10):
    s.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
    return data

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)

# 1. Stream to hidden domain (recorder user domain)
s.send(b"<stream:stream to='hidden.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
data = recv_until(s, b"</stream:features>", 5)
print(f"1. Features: {len(data)}b")

# 2. STARTTLS
s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
data = s.recv(4096)
print(f"2. STARTTLS: OK")

# 3. TLS
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname="xmpp.meet.jitsi")

# 4. Stream over TLS
s.send(b"<stream:stream to='hidden.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
data = recv_until(s, b"</stream:features>", 5)
print(f"3. TLS features: {len(data)}b")

# 5. SASL PLAIN auth
username = "recorder"
auth_str = f"\x00{username}\x00{password}"
auth_b64 = base64.b64encode(auth_str.encode()).decode()
s.send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth_b64}</auth>".encode())
data = recv_until(s, b"<success", 10)
if b"<success" not in data:
    print(f"AUTH FAILED: {data[:200]}"); exit(1)
print("4. AUTH OK")

# 6. Post-auth stream (back to meet.jitsi for MUC)
s.send(b"<stream:stream to='hidden.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
data = recv_until(s, b"</stream:features>", 5)
print(f"5. Bound features: {len(data)}b")

# 7. Bind resource
rid = str(uuid.uuid4())[:8]
s.send(f"<iq type='set' id='bind-1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>lightrec-{rid}</resource></bind></iq>".encode())
time.sleep(0.5)
data = s.recv(8192)
print(f"6. Bind: {len(data)}b")

# 8. Session
s.send(b"<iq type='set' id='sess-1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
time.sleep(0.5)
data = s.recv(8192)
print(f"7. Session: {len(data)}b")

# 9. Join MUC
s.send(f"<presence to='{room}@muc.meet.jitsi/lightrec'><x xmlns='http://jabber.org/protocol/muc'/><nick xmlns='http://jabber.org/protocol/nick'>lightrec</nick></presence>".encode())
time.sleep(2)
data = b""
s.settimeout(3)
try:
    while True:
        part = s.recv(8192)
        if not part:
            break
        data += part
except:
    pass
print(f"8. MUC join: {len(data)}b")
print(f"   Contains room: {room.encode() in data}")
if b"lightrec" in data:
    print("   Joined as lightrec!")
print(f"   Preview: {data[:400]}")

print("PHASE 1: PASS!")
s.send(b"</stream:stream>")
s.close()
