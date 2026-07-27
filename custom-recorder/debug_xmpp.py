#!/usr/bin/env python3
"""
Debug: Step-by-step XMPP test to see raw server response.
"""
import base64
import os
import socket
import ssl
import struct
import time
import uuid
from pathlib import Path

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 10808
XMPP_HOST = "xmpp.meet.jitsi"
XMPP_PORT = 5222

def socks5_connect(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect((PROXY_HOST, PROXY_PORT))
    s.send(b"\x05\x01\x00")
    resp = s.recv(2)
    assert resp == b"\x05\x00", f"Auth failed: {resp.hex()}"
    # Domain name connect
    host_bytes = host.encode()
    req = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", port)
    s.send(req)
    resp = s.recv(10)
    assert resp[1] == 0x00, f"Connect failed: code={resp[1]}"
    return s

def debug_recv(sock, label, timeout=5):
    sock.settimeout(timeout)
    try:
        d = sock.recv(8192)
        print(f"\n--- {label} ({len(d)} bytes) ---")
        print(repr(d[:500]))
        if b"<stream:stream" in d or b"<stream" in d:
            # Show formatted XML
            text = d.decode("utf-8", errors="replace")
            print(f"  As text: {text[:400]}")
        return d
    except socket.timeout:
        print(f"\n--- {label} --- TIMEOUT (no data)")
        return b""

print("=" * 60)
print("Debug XMPP Connection via SOCKS5")
print("=" * 60)

# 1. SOCKS5 connect
sock = socks5_connect(XMPP_HOST, XMPP_PORT)
print(f"\n✅ SOCKS5 connected to {XMPP_HOST}:{XMPP_PORT}")

# 2. Send stream and read
sock.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
debug_recv(sock, "Initial stream response", timeout=5)

# 3. STARTTLS
sock.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
debug_recv(sock, "STARTTLS response", timeout=5)

print("\n--- Try TLS wrap ---")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    tls_sock = ctx.wrap_socket(sock, server_hostname=XMPP_HOST, do_handshake_on_connect=True)
    tls_sock.settimeout(10)
    print("✅ TLS wrapped successfully")
except Exception as e:
    print(f"❌ TLS wrap failed: {e}")
    print("   This might be because SOCKS5 and TLS don't interact well.")
    print("   Trying without server_hostname...")
    try:
        # Reset socket - reconnect
        sock.close()
        sock = socks5_connect(XMPP_HOST, XMPP_PORT)
        sock.send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        time.sleep(0.5)
        # Read response
        resp = debug_recv(sock, "Stream (retry)", timeout=5)
        sock.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        time.sleep(0.5)
        resp2 = debug_recv(sock, "STARTTLS (retry)", timeout=5)

        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        tls_sock = ctx2.wrap_socket(sock, server_hostname="37.32.20.70", do_handshake_on_connect=False)
        tls_sock.do_handshake()
        print("✅ TLS wrapped with IP-based hostname!")
    except Exception as e2:
        print(f"❌ TLS wrap still failed: {e2}")

time.sleep(0.5)
try:
    s.close()
except:
    pass
