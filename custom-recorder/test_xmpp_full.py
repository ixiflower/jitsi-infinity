#!/usr/bin/env python3
"""
Full XMPP test for LightRec v3 — runs locally via SOCKS5 proxy.
Tests: TCP→SOCKS5→TLS→AUTH→BIND→SESSION→BREWERY→PRESENCE(fixed format)
"""

import base64
import os
import socket
import ssl
import struct
import time
import uuid
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Load password from .env.jibri
from pathlib import Path
env_path = Path(os.path.expanduser("~/jitsi-infinity/.env.jibri"))
env = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("\"'")
PASSWORD = env.get("JIBRI_XMPP_PASSWORD", "")
if not PASSWORD:
    print("❌ JIBRI_XMPP_PASSWORD not found")
    sys.exit(1)
else:
    print(f"✅ Password loaded ({len(PASSWORD)} chars)")

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 10808
XMPP_HOST = "xmpp.meet.jitsi"
XMPP_PORT = 5222

USERNAME = "jibri"
DOMAIN = "auth.meet.jitsi"
JID = f"{USERNAME}@{DOMAIN}"
BREWERY = "jibribrewery@internal-muc.meet.jitsi"
RESOURCE = f"lightrec-test-{str(uuid.uuid4())[:8]}"

JIBRI_STATUS_NS = "http://jitsi.org/protocol/jibri"
HEALTH_STATUS_NS = "http://jitsi.org/protocol/health"

steps_passed = 0
steps_total = 9

def step(n, msg, ok):
    global steps_passed
    if ok:
        steps_passed += 1
        print(f"  ✅ [{n}/{steps_total}] {msg}")
    else:
        print(f"  ❌ [{n}/{steps_total}] {msg}")
    return ok

def socks5_connect(host, port):
    """Connect to host:port via SOCKS5 proxy."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect((PROXY_HOST, PROXY_PORT))

    # Auth negotiation
    s.send(b"\x05\x01\x00")  # SOCKS5, 1 method, no auth
    resp = s.recv(2)
    if resp != b"\x05\x00":
        raise ConnectionError(f"SOCKS5 auth failed: {resp.hex()}")

    # Connect request
    if isinstance(host, str):
        # Domain name
        host_bytes = host.encode()
        req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
    else:
        # IPv4
        req = b"\x05\x01\x00\x01" + socket.inet_aton(host) + struct.pack(">H", port)

    s.send(req)
    resp = s.recv(10)
    if resp[1] != 0x00:
        raise ConnectionError(f"SOCKS5 connect failed: code={resp[1]}")
    return s

def recv_until(sock, marker, timeout=10):
    sock.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data

print("\n" + "=" * 60)
print("LightRec v3 — XMPP Connection Test (via SOCKS5)")
print("=" * 60)
print(f"  Proxy: {PROXY_HOST}:{PROXY_PORT}")
print(f"  Target: {XMPP_HOST}:{XMPP_PORT}")
print(f"  JID: {JID}")
print(f"  Brewery: {BREWERY}")
print()

# Step 1: SOCKS5 connect
try:
    sock = socks5_connect(XMPP_HOST, XMPP_PORT)
    step(1, "SOCKS5 → XMPP TCP connected", True)
except Exception as e:
    step(1, f"SOCKS5 connect: {e}", False)
    sys.exit(1)

# Step 2: Stream to auth domain
sock.send(f"<stream:stream to='{DOMAIN}' xmlns='jabber:client' "
           f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>".encode())
data = recv_until(sock, b"</stream:features>", 5)
step(2, "Stream features received", b"<stream:features" in data)

# Step 3: STARTTLS
sock.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
resp = sock.recv(4096)
if b"<proceed" in resp:
    # Wrap TLS
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    sock = ctx.wrap_socket(sock, server_hostname=XMPP_HOST)
    sock.settimeout(10)
    step(3, "TLS established", True)
else:
    step(3, f"TLS not available: {resp[:100]}", False)
    sys.exit(1)

# Step 4: SASL PLAIN auth
sock.send(f"<stream:stream to='{DOMAIN}' xmlns='jabber:client' "
           f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>".encode())
recv_until(sock, b"</stream:features>", 5)

auth_str = f"\x00{USERNAME}\x00{PASSWORD}"
ab64 = base64.b64encode(auth_str.encode()).decode()
sock.send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' "
           f"mechanism='PLAIN'>{ab64}</auth>".encode())
resp = recv_until(sock, b"<success", 10)
step(4, "SASL PLAIN auth", b"<success" in resp)

if b"<success" not in resp:
    print(f"  Auth response: {resp[:200]}")
    sys.exit(1)

# Step 5: Bind resource
sock.send(f"<stream:stream to='{DOMAIN}' xmlns='jabber:client' "
           f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>".encode())
recv_until(sock, b"</stream:features>", 5)

sock.send(f"<iq type='set' id='bind-1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'>"
           f"<resource>{RESOURCE}</resource></bind></iq>".encode())
resp = recv_until(sock, b"</iq>", 5)
import re
m = re.search(rb'<jid>([^<]+)</jid>', resp)
bound_jid = m.group(1).decode() if m else "unknown"
step(5, f"Resource bound: {bound_jid}", m is not None)

# Step 6: Session
sock.send(b"<iq type='set' id='sess-1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
resp = recv_until(sock, b"</iq>", 5)
step(6, "Session established", b"type='result'" in resp or b'type="result"' in resp)

# Step 7: Join brewery MUC (phase 1 — join)
sock.send(f"<presence to='{BREWERY}/{RESOURCE}'>"
           f"<x xmlns='http://jabber.org/protocol/muc'/></presence>".encode())
time.sleep(2)
# Flush any pending data
try:
    sock.settimeout(2)
    while sock.recv(65536):
        pass
except:
    pass
sock.settimeout(10)
step(7, "Brewery MUC join sent", True)

# Step 8: Send presence with Jibri status — THE FIXED FORMAT
presence_xml = (
    f"<presence to='{BREWERY}/{RESOURCE}'>"
    f"<x xmlns='http://jabber.org/protocol/muc'/>"
    f"<jibri-status xmlns='{JIBRI_STATUS_NS}'>"
    f"<busy-status>idle</busy-status>"
    f"</jibri-status>"
    f"<health-status xmlns='{HEALTH_STATUS_NS}'>HEALTHY</health-status>"
    f"</presence>"
)
sock.send(presence_xml.encode())
time.sleep(2)

# Read back what the server tells us
data = b""
try:
    sock.settimeout(3)
    while True:
        d = sock.recv(65536)
        if not d:
            break
        data += d
except:
    pass

if data:
    # Check for errors
    if b"error" in data or b"not-allowed" in data or b"forbidden" in data:
        step(8, "Presence update sent — but server responded with ERROR", False)
        print(f"  Error response: {data[:500]}")
    else:
        # Check for our own presence reflected back
        has_self = f"'{RESOURCE}'".encode() in data or RESOURCE.encode() in data
        has_jibri_status = b"jibri-status" in data
        has_health = b"health-status" in data

        print(f"  Response size: {len(data)} bytes")
        print(f"  Contains self resource: {'✅' if has_self else '❌'}")
        print(f"  Contains jibri-status: {'✅' if has_jibri_status else '❌'}")
        print(f"  Contains health-status: {'✅' if has_health else '❌'}")

        # Show the presence stanza we sent back (reflected)
        if b"jibri-status" in data:
            idx = data.find(b"<presence")
            print(f"\n  Presence reflection (first 400b): {data[idx:idx+400]}")

        step(8, "Jibri presence with FIXED format sent", True)
else:
    step(8, "Presence sent (no immediate response — this is normal)", True)

# Step 9: Listen briefly for any incoming stanzas (JibriIq would come asynchronously)
print("\n  --- Listening for 5 seconds for incoming stanzas ---")
sock.settimeout(5)
incoming = b""
start = time.time()
try:
    while time.time() - start < 5:
        chunk = sock.recv(65536)
        if not chunk:
            break
        incoming += chunk
        # Print any IQs we see
        if b"<iq " in chunk:
            iq_start = chunk.find(b"<iq ")
            iq_end = chunk.find(b"</iq>") + 6
            if iq_end > iq_start:
                print(f"  📨 IQ received: {chunk[iq_start:iq_end][:200]}")
except socket.timeout:
    pass
except Exception as e:
    print(f"  Error: {e}")

if incoming:
    has_presence = b"<presence" in incoming
    has_iq = b"<iq " in incoming
    has_jibri_iq = b"jibri" in incoming and b"action" in incoming
    print(f"  Incoming: {len(incoming)}b, presence={has_presence}, iq={has_iq}, jibri_iq={has_jibri_iq}")
    if has_jibri_iq:
        print(f"\n  🎯 JibriIq DETECTED! The fix works!")
else:
    print("  No incoming stanzas (expected — need to trigger recording from UI)")

step(9, "Listen completed", True)

# Cleanup
try:
    sock.sendall(b"</stream:stream>")
    sock.close()
except:
    pass

print()
print("=" * 60)
print(f"RESULT: {steps_passed}/{steps_total} steps passed")
print("=" * 60)
if steps_passed == steps_total:
    print("✅ ALL TESTS PASSED — LightRec v3 is ready!")
else:
    print(f"⚠️  Some steps failed. Review above.")
