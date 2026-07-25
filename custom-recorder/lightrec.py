#!/usr/bin/env python3
"""
LightRec v2 — Orchestrator mode.
Gets recording triggers from Jicofo, delegates to Jibri containers.
No WebRTC stack needed — uses the existing Jibri Docker infrastructure.
"""

import asyncio
import base64
import json
import logging
import os
import ssl
import socket
import subprocess
import time
import uuid
from pathlib import Path

log = logging.getLogger("lightrec")

# ── Config ────────────────────────────────────────────────────────────
JIBRI_COUNT = int(os.environ.get("JIBRI_COUNT", "5"))
JIBRI_IMAGE = os.environ.get("JIBRI_IMAGE", "jitsi/jibri:unstable")
JITSI_NETWORK = os.environ.get("JITSI_NETWORK", "jitsi-infinity_meet.jitsi")
RECORDINGS_DIR = os.environ.get("RECORDINGS_DIR", "/recordings")


# ── XMPP Client (raw socket) ──────────────────────────────────────────
class XMPP:
    """Minimal XMPP — connects, joins brewery, listens for JibriIq."""

    def __init__(self, jid, password, on_trigger=None):
        self.jid = jid
        self.username = jid.split("@")[0]
        self.domain = jid.split("@")[1]
        self.password = password
        self.sock = None
        self.brewery = "jibribrewery@internal-muc.meet.jitsi"
        self.running = True
        self.on_trigger = on_trigger
        self.session_id = str(uuid.uuid4())[:8]

    def connect(self, host="xmpp.meet.jitsi", port=5222):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)

        # Stream to auth domain
        self._send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)
        log.info("1. Features OK")

        # TLS
        self._send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        if b"<proceed" not in self.sock.recv(4096):
            log.error("TLS unavailable"); return False
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.sock = ctx.wrap_socket(self.sock, server_hostname=host)
        self.sock.settimeout(10)
        log.info("2. TLS OK")

        # Auth
        self._send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)
        auth = f"\x00{self.username}\x00{self.password}"
        ab64 = base64.b64encode(auth.encode()).decode()
        self._send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{ab64}</auth>")
        resp = self._recv_until(b"<success", 10)
        if b"<success" not in resp:
            log.error(f"Auth failed: {resp[:200]}"); return False
        log.info("3. AUTH OK")

        # Bind + Session
        self._send(b"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)
        rid = str(uuid.uuid4())[:8]
        self._send(f"<iq type='set' id='b1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>lightrec-{rid}</resource></bind></iq>")
        time.sleep(0.5); self._recv(8192)
        self._send(b"<iq type='set' id='s1'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
        time.sleep(0.5); self._recv(8192)

        # 1. Join brewery MUC (initial presence, no status)
        self._send(
            f"<presence to='{self.brewery}/lightrec'>"
            f"<x xmlns='http://jabber.org/protocol/muc'/></presence>"
        )
        time.sleep(2)
        self._recv(65536, timeout=3)
        log.info("4a. Brewery MUC joined")

        # 2. Send Jibri status update (idle = available for recording)
        status_id = str(uuid.uuid4())
        self._send(
            f"<presence to='{self.brewery}/lightrec'>"
            f"<x xmlns='http://jabber.org/protocol/muc'/>"
            f"<jibri-status xmlns='http://jitsi.org/protocol/jibri'>"
            f"<busy-status>idle</busy-status>"
            f"<health-status>HEALTHY</health-status>"
            f"</jibri-status>"
            f"</presence>"
        )
        time.sleep(2)
        self._recv(65536, timeout=3)
        log.info("4b. Jibri status sent (idle)")

        return True

    def listen(self):
        self.sock.settimeout(None)
        buf = b""
        while self.running:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                while b"</iq>" in buf:
                    idx = buf.find(b"</iq>") + 6
                    stanza = buf[:idx].decode("utf-8", errors="replace")
                    buf = buf[idx:]
                    if "jibri" in stanza and "action" in stanza:
                        log.info("=== JibriIq RECEIVED ===")
                        if self.on_trigger:
                            self.on_trigger(stanza)
            except Exception as e:
                if self.running:
                    log.error(f"Error: {e}")
                break

    def _send(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.sock.send(data)

    def _recv(self, size, timeout=10):
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(size)
        except socket.timeout:
            return b""

    def _recv_until(self, marker, timeout=10):
        self.sock.settimeout(timeout)
        data = b""
        while marker not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data

    def disconnect(self):
        self.running = False
        try:
            self.sock.send(b"</stream:stream>")
            self.sock.close()
        except:
            pass


# ── Trigger Handler ───────────────────────────────────────────────────
def handle_trigger(stanza):
    """When Jicofo sends a JibriIq, parse and launch a Jibri container."""
    log.info(f"Handling recording trigger...")

    # Extract session_id and room from the IQ
    import re
    session_match = re.search(r'session_id="([^"]+)"', stanza)
    room_match = re.search(r'room="([^"]+)"', stanza)
    action_match = re.search(r'action="([^"]+)"', stanza)

    session_id = session_match.group(1) if session_match else "unknown"
    room = room_match.group(1) if room_match else "unknown"
    action = action_match.group(1) if action_match else "unknown"

    log.info(f"  Action: {action}")
    log.info(f"  Room: {room}")
    log.info(f"  Session: {session_id}")

    if action == "start":
        log.info(f"Starting recording for room: {room}")
        # In orchestrator mode, we would launch a Jibri container here
        # But for now we just acknowledge
        log.info("LightRec v2: Trigger received (Jibri would record)")
    elif action == "stop":
        log.info("Stop recording requested")


# ── Main ──────────────────────────────────────────────────────────────
def load_env(path):
    env = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return env


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    env = load_env("/app/.env.jibri") or {}
    password = env.get("JIBRI_XMPP_PASSWORD", "")
    if not password:
        log.error("JIBRI_XMPP_PASSWORD not found")
        return

    xmpp = XMPP("jibri@auth.meet.jitsi", password, handle_trigger)

    if xmpp.connect():
        log.info("LightRec v2: Connected. Waiting for triggers...")
        xmpp.listen()
    else:
        log.error("Connection failed")

    xmpp.disconnect()


if __name__ == "__main__":
    main()
