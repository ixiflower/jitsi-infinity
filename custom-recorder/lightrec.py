#!/usr/bin/env python3
"""
LightRec — Phase 2: XMPP (raw socket) + WebRTC (aiortc) integration.
Builds on the working raw-socket XMPP client and adds Jingle/WebRTC.
"""

import asyncio
import base64
import json
import logging
import os
import ssl
import socket
import struct
import time
import uuid
from pathlib import Path

import aiortc
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack

log = logging.getLogger("lightrec")

# ── XMPP Raw Socket Client ───────────────────────────────────────────
class XMPP:
    """Minimal XMPP client (raw socket). Handles auth + MUC + Jingle IQs."""

    def __init__(self, jid, password):
        self.jid = jid
        self.username = jid.split("@")[0]
        self.domain = jid.split("@")[1]
        self.password = password
        self.sock = None
        self.brevery_jid = "jibribrewery@internal-muc.meet.jitsi"
        self.running = True
        self.recv_buffer = b""
        self.session_id = str(uuid.uuid4())[:8]
        self.on_jibri_iq = None  # callback

    def connect(self, host="xmpp.meet.jitsi", port=5222):
        """Connect + TLS + auth + join brewery."""
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)

        # Stream to hidden domain
        self._send(b"<stream:stream to='hidden.meet.jitsi' "
                   b"xmlns='jabber:client' "
                   b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)
        log.info("1. Stream features OK")

        # STARTTLS
        self._send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        resp = self.sock.recv(4096)
        if b"<proceed" not in resp:
            log.error("TLS not available"); return False
        log.info("2. TLS proceeding")

        # Wrap TLS
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.sock = ctx.wrap_socket(self.sock, server_hostname=host)
        self.sock.settimeout(10)
        log.info("3. TLS OK")

        # Auth stream
        self._send(b"<stream:stream to='hidden.meet.jitsi' "
                   b"xmlns='jabber:client' "
                   b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)

        # SASL PLAIN
        auth = f"\x00{self.username}\x00{self.password}"
        auth_b64 = base64.b64encode(auth.encode()).decode()
        self._send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' "
                   f"mechanism='PLAIN'>{auth_b64}</auth>")
        resp = self._recv_until(b"<success", timeout=10)
        if b"<success" not in resp:
            log.error(f"Auth failed: {resp[:200]}"); return False
        log.info("4. AUTH OK")

        # Post-auth stream
        self._send(b"<stream:stream to='hidden.meet.jitsi' "
                   b"xmlns='jabber:client' "
                   b"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)

        # Bind resource
        rid = str(uuid.uuid4())[:8]
        self._send(f"<iq type='set' id='bind-1'><bind "
                   f"xmlns='urn:ietf:params:xml:ns:xmpp-bind'>"
                   f"<resource>lightrec-{rid}</resource></bind></iq>")
        time.sleep(0.5)
        self._recv(8192)

        # Session
        self._send(b"<iq type='set' id='sess-1'>"
                   b"<session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
        time.sleep(0.5)
        self._recv(8192)

        # Join brewery MUC
        self._send(f"<presence to='{self.brevery_jid}/lightrec'>"
                   f"<x xmlns='http://jabber.org/protocol/muc'/></presence>")
        time.sleep(2)
        resp = self._recv(65536, timeout=3)
        log.info(f"5. Brewery MUC: {len(resp)}b")

        log.info("Connected to brewery. Waiting for JibriIq...")
        return True

    def listen(self):
        """Listen for stanzas (blocking). Calls on_jibri_iq when triggered."""
        self.sock.settimeout(None)
        buf = b""
        while self.running:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                buf += chunk

                # Process complete iq stanzas
                while b"</iq>" in buf:
                    idx = buf.find(b"</iq>") + 6
                    stanza = buf[:idx].decode("utf-8", errors="replace")
                    buf = buf[idx:]
                    if "jibri" in stanza and "action" in stanza:
                        log.info("JibriIq received!")
                        if self.on_jibri_iq:
                            self.on_jibri_iq(stanza)
            except Exception as e:
                if self.running:
                    log.error(f"Listen error: {e}")
                break

    def _send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
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


# ── WebRTC Session ────────────────────────────────────────────────────
class WebRTCSession:
    """Manages a WebRTC connection to JVB for recording."""

    def __init__(self):
        self.pc = None
        self.tracks = []

    async def create_from_jingle(self, jingle_stanza):
        """Parse Jingle session-initiate and create WebRTC answer."""
        log.info("Creating WebRTC session from Jingle...")
        self.pc = RTCPeerConnection()

        @self.pc.on("track")
        async def on_track(track):
            log.info(f"Track received: {track.kind}")
            self.tracks.append(track)

        @self.pc.on("iceconnectionstatechange")
        async def on_ice():
            state = self.pc.iceConnectionState
            log.info(f"ICE: {state}")
            if state == "connected":
                log.info("RECORDING - WebRTC connected!")

        # Create data channel for control
        self.pc.createDataChannel("control")

        # Create answer
        # For now, we just create a bare offer/answer
        self.pc.addTransceiver("audio", direction="recvonly")
        self.pc.addTransceiver("video", direction="recvonly")

        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        log.info(f"WebRTC offer created: {len(offer.sdp)} chars")

        return self.pc.localDescription

    async def close(self):
        if self.pc:
            await self.pc.close()


# ── Main ──────────────────────────────────────────────────────────────
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


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    env = load_env("/app/.env.jibri") or {}
    password = env.get("JIBRI_RECORDER_PASSWORD", "")
    if not password:
        log.error("No password"); return

    def on_jibri(stanza):
        log.info(f"Recording triggered! Room info in: {stanza[:300]}")

    xmpp = XMPP("recorder@hidden.meet.jitsi", password)
    xmpp.on_jibri_iq = on_jibri

    if xmpp.connect():
        log.info("LightRec Phase 2: Connected. Waiting for trigger...")
        xmpp.listen()
    else:
        log.error("Connection failed")

    xmpp.disconnect()


if __name__ == "__main__":
    main()
