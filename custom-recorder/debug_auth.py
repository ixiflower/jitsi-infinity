#!/usr/bin/env python3
"""Raw binary dump of everything to debug auth timeout."""
import socket, ssl, base64, sys
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

env = load_env("/app/.env.jibri") or {}
password = env.get("JIBRI_RECORDER_PASSWORD", "")
username = "recorder"

s = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)

# Stream
s.send(b"<stream:stream to='hidden.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
raw = b""
while b"</stream:features>" not in raw:
    raw += s.recv(4096)
print(f"FEATURES: {len(raw)}b", file=sys.stderr)

# STARTTLS
s.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
raw = s.recv(4096)
print(f"STARTTLS RESP: {raw}", file=sys.stderr)

# TLS
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = ctx.wrap_socket(s, server_hostname="xmpp.meet.jitsi")
print("TLS OK", file=sys.stderr)

# Stream over TLS
s.send(b"<stream:stream to='hidden.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
raw = b""
while b"</stream:features>" not in raw:
    raw += s.recv(4096)
print(f"TLS FEATURES: {len(raw)}b", file=sys.stderr)

# Auth PLAIN
auth_str = f"\x00{username}\x00{password}"
auth_b64 = base64.b64encode(auth_str.encode()).decode()
auth_xml = f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth_b64}</auth>"
print(f"AUTH XML: {auth_xml[:100]}...", file=sys.stderr)
s.send(auth_xml.encode())

# Read response with short timeout
s.settimeout(5)
try:
    raw = s.recv(4096)
    print(f"AUTH RESP ({len(raw)}b): {raw}", file=sys.stderr)
except socket.timeout:
    print("AUTH RESP: TIMEOUT (no response in 5s)", file=sys.stderr)
    
    # Try sending a ping / whitespace to see if server is alive
    s.send(b" ")
    try:
        raw = s.recv(4096)
        print(f"After ping: {raw}", file=sys.stderr)
    except:
        print("Still dead", file=sys.stderr)
    
s.close()
