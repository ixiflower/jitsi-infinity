#!/usr/bin/env python3
"""
LightRec — Phase 1: XMPP Client (JibriIq listener mode).

Connects to Prosody as recorder@hidden.meet.jitsi, joins the brewery MUC
(so Jicofo can send us recording tasks), and listens for JibriIq.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("lightrec.xmpp")

# ── Helpers ───────────────────────────────────────────────────────────
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


# ── Low-level XMPP client (no lib needed) ─────────────────────────────
class XMPPClient:
    """
    Minimal async XMPP client using asyncio + socket.
    Connects to Prosody, auth as recorder, joins brewery MUC,
    listens for JibriIq.
    """

    def __init__(self, jid, password, room_callback=None):
        self.jid = jid
        self.username = jid.split("@")[0]
        self.domain = jid.split("@")[1]
        self.password = password
        self.room_callback = room_callback  # called when recording triggered
        self.reader = None
        self.writer = None
        self.session_id = str(uuid.uuid4())[:8]
        self.brevery_jid = "jibribrewery@internal-muc.meet.jitsi"
        self.running = True

    async def connect(self, host="xmpp.meet.jitsi", port=5222):
        """Connect to Prosody with TLS."""
        log.info(f"Connecting to {host}:{port} as {self.jid}")

        # TCP connect
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=10)

        # Stream to hidden domain
        await self._send(
            "<stream:stream to='hidden.meet.jitsi' "
            "xmlns='jabber:client' "
            "xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
        )
        features = await self._recv_until(b"</stream:features>", timeout=5)
        log.debug(f"Features: {len(features)}b")

        # STARTTLS
        await self._send("<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        resp = await self._recv(4096, timeout=5)
        if b"<proceed" not in resp:
            log.error("TLS not available")
            return False

        # Upgrade to TLS
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        transport = self.writer.transport
        sock = transport.get_extra_info("socket")
        # We can't easily upgrade asyncio transport to TLS
        # This requires start_tls which is available in Python 3.11+
        log.error("TLS upgrade not supported in current asyncio setup")
        return False


class XMPPClientTLS:
    """
    XMPP client using raw socket + manual recv/send (no asyncio).
    Runs in executor thread.
    """

    def __init__(self, jid, password, room_callback=None):
        self.jid = jid
        self.username = jid.split("@")[0]
        self.domain = jid.split("@")[1]
        self.password = password
        self.room_callback = room_callback
        self.sock = None
        self.session_id = str(uuid.uuid4())[:8]
        self.running = True

    def connect(self, host="xmpp.meet.jitsi", port=5222):
        """Synchronous connect to Prosody with TLS."""
        import socket, ssl, time, base64

        log.info(f"Connecting to {host}:{port} as {self.jid}")

        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)

        def recv_until(marker, timeout=10):
            self.sock.settimeout(timeout)
            data = b""
            while marker not in data:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data

        # 1. Stream to hidden domain
        self.sock.send(
            b"<stream:stream to='hidden.meet.jitsi' "
            b"xmlns='jabber:client' "
            b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
        )
        recv_until(b"</stream:features>", 5)
        log.info("1. Stream features received")

        # 2. STARTTLS
        self.sock.send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        resp = self.sock.recv(4096)
        if b"<proceed" not in resp:
            log.error("TLS not available")
            return False
        log.info("2. TLS proceeding")

        # 3. Wrap TLS
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.sock = ctx.wrap_socket(self.sock, server_hostname=host)
        self.sock.settimeout(10)
        log.info("3. TLS established")

        # 4. Auth stream
        self.sock.send(
            b"<stream:stream to='hidden.meet.jitsi' "
            b"xmlns='jabber:client' "
            b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
        )
        recv_until(b"</stream:features>", 5)

        # 5. SASL PLAIN
        auth_str = f"\x00{self.username}\x00{self.password}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        self.sock.send(
            f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' "
            f"mechanism='PLAIN'>{auth_b64}</auth>".encode()
        )
        resp = recv_until(b"<success", timeout=10)
        if b"<success" not in resp:
            log.error(f"Auth failed: {resp[:200]}")
            return False
        log.info("4. AUTH OK")

        # 6. Post-auth stream
        self.sock.send(
            b"<stream:stream to='hidden.meet.jitsi' "
            b"xmlns='jabber:client' "
            b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
        )
        recv_until(b"</stream:features>", 5)

        # 7. Bind resource
        rid = str(uuid.uuid4())[:8]
        self.sock.send(
            f"<iq type='set' id='bind-1'><bind "
            f"xmlns='urn:ietf:params:xml:ns:xmpp-bind'>"
            f"<resource>lightrec-{rid}</resource></bind></iq>".encode()
        )
        time.sleep(0.5)
        self.sock.recv(8192)

        # 8. Session
        self.sock.send(
            b"<iq type='set' id='sess-1'>"
            b"<session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>"
        )
        time.sleep(0.5)
        self.sock.recv(8192)

        # 9. Join brewery MUC (so Jicofo can send us tasks)
        self.sock.send(
            f"<presence to='{self.brevery_jid}/lightrec'>"
            b"<x xmlns='http://jabber.org/protocol/muc'/></presence>".encode()
        )
        time.sleep(2)
        resp = b""
        self.sock.settimeout(3)
        try:
            while True:
                resp += self.sock.recv(8192)
        except:
            pass
        log.info(f"5. Brewery MUC response: {len(resp)}b")
        log.info(f"   Preview: {resp[:200]}")

        log.info("Phase 1 complete! Waiting for recording tasks...")
        return True

    def listen(self):
        """Listen for incoming IQs (JibriIq from Jicofo)."""
        import xml.etree.ElementTree as ET
        self.sock.settimeout(None)
        buf = b""

        while self.running:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                buf += chunk

                # Process complete stanzas
                while b"</iq>" in buf or b"</message>" in buf or b"</presence>" in buf:
                    # Simple parsing - look for IQ with jibri namespace
                    if b"jibri" in buf and b"</iq>" in buf:
                        iq_end = buf.find(b"</iq>") + 6
                        stanza = buf[:iq_end].decode("utf-8", errors="replace")
                        buf = buf[iq_end:]

                        if "jibri" in stanza and "action" in stanza:
                            log.info(f"JibriIq received!")
                            log.info(f"Stanza: {stanza[:200]}")
                            if self.room_callback:
                                self.room_callback(stanza)
                    else:
                        # Consume one stanza
                        for tag in [b"</iq>", b"</message>", b"</presence>"]:
                            if tag in buf:
                                idx = buf.find(tag) + len(tag)
                                buf = buf[idx:]
                                break
                        else:
                            break

            except Exception as e:
                log.error(f"Error in listen loop: {e}")
                break

    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.send(b"</stream:stream>")
                self.sock.close()
            except:
                pass


# ── Main ──────────────────────────────────────────────────────────────
def main():
    env = load_env("/app/.env.jibri") or \
          load_env("/home/ubuntu/jitsi-infinity/.env.jibri") or \
          load_env(".env.jibri") or {}

    password = env.get("JIBRI_RECORDER_PASSWORD", "")
    if not password:
        log.error("JIBRI_RECORDER_PASSWORD not found")
        return

    def on_recording(stanza):
        log.info(f"Recording triggered! Stanza: {stanza[:300]}")

    xmpp = XMPPClientTLS("recorder@hidden.meet.jitsi", password, on_recording)

    if xmpp.connect():
        log.info("Connected to Jitsi infrastructure. Listening...")
        xmpp.listen()
    else:
        log.error("Failed to connect")

    xmpp.disconnect()


if __name__ == "__main__":
    from pathlib import Path
    main()
