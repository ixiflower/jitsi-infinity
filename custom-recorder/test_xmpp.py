#!/usr/bin/env python3
"""LightRec XMPP connectivity test v3 — works within stream limits."""
import asyncio, logging, os, socket, ssl, base64, uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lightrec")

async def recv_until(sock, marker, timeout=10):
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data

async def test_xmpp():
    for p in ["/app/.env.jibri", "/home/ubuntu/jitsi-infinity/.env.jibri",
              ".env.jibri"]:
        if Path(p).exists():
            env = load_env(p)
            break
    else:
        log.error("Cannot find .env.jibri"); return False

    password = env.get("JIBRI_RECORDER_PASSWORD", "")
    jid = "recorder@hidden.meet.jitsi"
    username = jid.split("@")[0]

    log.info(f"Connecting to xmpp.meet.jitsi:5222 as {jid}")

    sock = socket.create_connection(("xmpp.meet.jitsi", 5222), timeout=10)
    sock.settimeout(10)

    # Open XMPP stream
    sock.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
    data = await recv_until(sock, b"</stream:features>")
    log.info(f"Got stream features ({len(data)} bytes)")

    # STARTTLS
    sock.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    data = sock.recv(4096)
    if b"<proceed" in data:
        log.info("TLS proceeding...")
    else:
        log.error(f"TLS failed: {data[:200]}"); return False

    # Wrap TLS
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    sock = ctx.wrap_socket(sock, server_hostname="xmpp.meet.jitsi")
    log.info("TLS established")

    # Restart stream
    sock.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
    data = await recv_until(sock, b"</stream:features>")
    log.info(f"Post-TLS features ({len(data)} bytes)")

    # SASL PLAIN
    auth_str = f"\x00{username}\x00{password}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    sock.send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{auth_b64}</auth>".encode())
    data = await recv_until(sock, b"</success>")
    
    if b"<success" in data:
        log.info("AUTH SUCCESS!")
    else:
        log.error(f"Auth failed: {data[:200]}"); sock.close(); return False

    # Post-auth stream
    sock.send(b"<stream:stream to='meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
    data = await recv_until(sock, b"</stream:features>")
    log.info("Post-auth stream ready")

    # Bind
    rid = str(uuid.uuid4())[:8]
    sock.send(f"<iq type='set' id='bind-1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>lightrec-{rid}</resource></bind></iq>".encode())
    await asyncio.sleep(0.5)
    sock.recv(8192)

    # Session
    sock.send(b"<iq type='set' id='sess-1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
    await asyncio.sleep(0.5)
    sock.recv(8192)

    # Join MUC
    room = os.environ.get("LIGHTREC_ROOM", "lightrec-test-room")
    sock.send(f"<presence to='{room}@muc.meet.jitsi/lightrec'><x xmlns='http://jabber.org/protocol/muc'/></presence>".encode())
    await asyncio.sleep(2)
    data = sock.recv(8192)
    log.info(f"MUC response: {len(data)} bytes")
    log.info(f"MUC data preview: {data[:200]}")

    log.info("Phase 1: PASS!")
    sock.send(b"</stream:stream>")
    sock.close()
    return True

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

if __name__ == "__main__":
    result = asyncio.run(test_xmpp())
    log.info(f"Result: {'PASS' if result else 'FAIL'}")
