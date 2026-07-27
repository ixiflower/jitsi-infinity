#!/usr/bin/env python3
"""
LightRec v3 — Orchestrator mode.
Connects to brewery as a Jibri instance, receives recording triggers from Jicofo,
and delegates to Jibri Docker containers.

Key fix vs v2: health-status is now a SIBLING element of jibri-status (not nested),
matching exactly what Jibri's Java code sends, so Jicofo's Smack extension parser
correctly detects availability.
"""

import base64
import json
import logging
import os
import re
import ssl
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

log = logging.getLogger("lightrec")

# ── Config ────────────────────────────────────────────────────────────
JIBRI_IMAGE = os.environ.get("JIBRI_IMAGE", "jitsi/jibri:unstable")
JITSI_NETWORK = os.environ.get("JITSI_NETWORK", "jitsi-infinity_meet.jitsi")
RECORDINGS_DIR = os.environ.get("RECORDINGS_DIR", "/recordings")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
# Which JID/password to use for connecting
JIBRI_USER = os.environ.get("JIBRI_XMPP_USER", "jibri")
JIBRI_DOMAIN = os.environ.get("JIBRI_XMPP_DOMAIN", "auth.meet.jitsi")
JID = f"{JIBRI_USER}@{JIBRI_DOMAIN}"
XMPP_HOST = os.environ.get("XMPP_SERVER", "xmpp.meet.jitsi")
XMPP_PORT = int(os.environ.get("XMPP_PORT", "5222"))
BREWERY_MUC = os.environ.get("JIBRI_BREWERY_MUC", "jibribrewery@internal-muc.meet.jitsi")
MAX_RECONNECT_DELAY = 30


# ── XMPP Client (raw socket) ──────────────────────────────────────────
class XMPP:
    """
    Minimal XMPP client using raw sockets + TLS.
    Connects to Prosody, auth as jibri@auth.meet.jitsi, joins brewery MUC,
    sends proper Jibri presence (with health-status as sibling element),
    listens for JibriIq triggers from Jicofo.
    """

    JIBRI_STATUS_NS = "http://jitsi.org/protocol/jibri"
    HEALTH_STATUS_NS = "http://jitsi.org/protocol/health"

    def __init__(self, jid, password, on_trigger=None):
        self.jid = jid
        self.username = jid.split("@")[0]
        self.domain = jid.split("@")[1]
        self.password = password
        self.sock = None
        self.brewery = BREWERY_MUC
        self.running = True
        self.on_trigger = on_trigger
        self.session_id = str(uuid.uuid4())[:8]
        self.resource = f"lightrec-{self.session_id}"
        self.full_jid = None  # set after bind
        self._buf = b""

    def connect(self, host=None, port=None):
        host = host or XMPP_HOST
        port = port or XMPP_PORT

        log.info(f"Connecting to {host}:{port} as {self.jid}")

        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)
        log.debug(f"TCP connected to {host}:{port}")

        # 1. Stream to auth domain
        stream1 = (f"<stream:stream to='{self.domain}' xmlns='jabber:client' "
                   f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._send(stream1)
        log.debug(f"Sent auth stream, waiting for features...")
        features1 = self._recv_until(b"</stream:features>", 5)
        log.debug(f"Auth features ({len(features1)}b): {features1[:300]}")

        # 2. STARTTLS
        self._send(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
        resp = self.sock.recv(4096)
        if b"<proceed" not in resp:
            log.error("TLS not available"); return False
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.sock = ctx.wrap_socket(self.sock, server_hostname=host)
        self.sock.settimeout(10)

        # 3. Auth stream (same domain!)
        self._send(f"<stream:stream to='{self.domain}' xmlns='jabber:client' "
                    f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)

        # 4. SASL PLAIN
        auth_str = f"\x00{self.username}\x00{self.password}"
        ab64 = base64.b64encode(auth_str.encode()).decode()
        self._send(f"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' "
                    f"mechanism='PLAIN'>{ab64}</auth>")
        resp = self._recv_until(b"<success", 10)
        if b"<success" not in resp:
            log.error(f"Auth failed: {resp[:200]}"); return False

        # 5. Post-auth stream (same domain!)
        self._send(f"<stream:stream to='{self.domain}' xmlns='jabber:client' "
                    f"xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>")
        self._recv_until(b"</stream:features>", 5)

        # 6. Bind resource
        self._send(
            f"<iq type='set' id='bind-1'><bind "
            f"xmlns='urn:ietf:params:xml:ns:xmpp-bind'>"
            f"<resource>{self.resource}</resource></bind></iq>"
        )
        bind_resp = self._recv_until(b"</iq>", 5)
        m = re.search(rb'<jid>([^<]+)</jid>', bind_resp)
        if m:
            self.full_jid = m.group(1).decode()
            log.info(f"Bound as: {self.full_jid}")

        # 7. Session
        self._send(b"<iq type='set' id='sess-1'>"
                    b"<session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>")
        self._recv_until(b"</iq>", 5)

        # 8. Join brewery MUC
        # Send presence in TWO steps: first join (no status), then update with status
        self._send(
            f"<presence to='{self.brewery}/{self.resource}'>"
            f"<x xmlns='http://jabber.org/protocol/muc'/></presence>"
        )
        time.sleep(1.5)
        self._flush_read()

        # 9. Send Jibri status presence
        presence = self._build_status_presence()
        log.debug(f"Sending presence XML: {presence}")
        self._send(presence)
        time.sleep(1)
        self._flush_read()
        time.sleep(1)
        self._flush_read()

        log.info("Connected to brewery. Waiting for recording triggers...")
        return True

    def listen(self):
        """Listen for incoming stanzas (IQs, presences, messages)."""
        self.sock.settimeout(None)
        self._buf = b""

        while self.running:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    log.warning("Connection closed by server")
                    break
                self._buf += chunk
                self._process_stanzas()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    log.error(f"Error in listen: {e}")
                break

    def _process_stanzas(self):
        """Extract and process complete XML stanzas from the buffer."""
        while True:
            stanza, rest = self._extract_stanza()
            if stanza is None:
                break
            self._buf = rest
            self._handle_stanza(stanza)

    def _extract_stanza(self):
        """Extract the first complete stanza from the buffer."""
        buf = self._buf

        # IQ stanzas
        if b"<iq " in buf and b"</iq>" in buf:
            start = buf.find(b"<iq ")
            end = buf.find(b"</iq>") + 5
            if end > start:
                return buf[start:end], buf[end:]

        # Presence stanzas
        if b"<presence" in buf and b"</presence>" in buf:
            start = buf.find(b"<presence")
            end = buf.find(b"</presence>") + 11
            if end > start:
                return buf[start:end], buf[end:]

        # Message stanzas
        if b"<message " in buf and b"</message>" in buf:
            start = buf.find(b"<message ")
            end = buf.find(b"</message>") + 10
            if end > start:
                return buf[start:end], buf[end:]

        return None, buf

    def _handle_stanza(self, stanza):
        """Route a parsed stanza to the appropriate handler."""
        decoded = stanza.decode("utf-8", errors="replace")

        # IQ: check for JibriIq (recording trigger)
        if stanza.startswith(b"<iq ") and b"jibri" in stanza and b"action" in stanza:
            log.info("=== JibriIq RECEIVED ===")
            log.debug(f"Raw: {decoded[:500]}")
            self._handle_jibri_iq(decoded)

        # Presence: log for debugging
        elif stanza.startswith(b"<presence"):
            if b"jibri-status" in stanza or b"busy-status" in stanza:
                log.debug(f"Jibri presence: {decoded[:300]}")

    def _handle_jibri_iq(self, stanza):
        """Process a JibriIq recording trigger from Jicofo."""
        # Extract attributes
        iq_id = self._xml_attr(stanza, "id")
        iq_from = self._xml_attr(stanza, "from")
        session_id = self._xml_attr(stanza, "session_id") or "unknown"
        room = self._xml_attr(stanza, "room") or "unknown"
        action = self._xml_attr(stanza, "action") or "unknown"

        log.info(f"  Room: {room}")
        log.info(f"  Session: {session_id}")
        log.info(f"  Action: {action}")
        log.info(f"  From: {iq_from}")

        # Send ACK back to Jicofo — this is CRITICAL otherwise Jicofo
        # times out the IQ (15s default) and marks the recording as failed.
        self._send(
            f"<iq type='result' id='{iq_id}' "
            f"to='{iq_from}'/>"
        )
        log.info("ACK sent to Jicofo")

        if action == "start":
            if self.on_trigger:
                self.on_trigger(room, session_id)
        elif action == "stop":
            log.info("Stop recording requested (not implemented yet)")
        else:
            log.warning(f"Unknown action: {action}")

    def _xml_attr(self, xml_str, attr):
        """Extract an attribute value from an XML string. Supports both quote styles."""
        m = re.search(rf'{attr}=["\']([^"\']+)["\']', xml_str)
        return m.group(1) if m else None

    def _send(self, data):
        if isinstance(data, str):
            data = data.encode()
        try:
            self.sock.sendall(data)
        except Exception as e:
            log.error(f"Send error: {e}")

    def _recv(self, size, timeout=10):
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(size)
        except socket.timeout:
            return b""

    def _recv_until(self, marker, timeout=10):
        self.sock.settimeout(timeout)
        data = b""
        try:
            while marker not in data:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            log.debug(f"_recv_until timeout after {len(data)}b, marker={marker}")
        except Exception as e:
            log.debug(f"_recv_until error: {e}")
        return data

    def _flush_read(self):
        """Flush any pending data from the socket."""
        self.sock.settimeout(0.5)
        try:
            while self.sock.recv(65536):
                pass
        except (socket.timeout, BlockingIOError):
            pass
        self.sock.settimeout(None)

    def disconnect(self):
        self.running = False
        try:
            self.sock.sendall(b"</stream:stream>")
            self.sock.close()
        except:
            pass

    def _build_status_presence(self):
        """Build the Jibri presence stanza.

        FIXED: health-status is a SIBLING of jibri-status (direct child of presence),
        matching exactly what the real Jibri Java code sends via
        org.jitsi.jibri.JibriManager.

        Jicofo's HealthStatusPacketExt looks for health-status as a
        direct child extension of the <presence> stanza, NOT nested inside
        <jibri-status>. This is required for Jicofo to detect available = true.
        """
        return (
            f"<presence to='{self.brewery}/{self.resource}'>"
            f"<x xmlns='http://jabber.org/protocol/muc'/>"
            f"<jibri-status xmlns='{self.JIBRI_STATUS_NS}'>"
            f"<busy-status status='idle'/>"
            f"<health-status xmlns='{self.HEALTH_STATUS_NS}' status='HEALTHY'/>"
            f"</jibri-status>"
            f"</presence>"
        )


# ── Jibri Container Orchestration ─────────────────────────────────────
class JibriOrchestrator:
    """
    Manages a pool of Jibri Docker containers.
    When LightRec receives a recording trigger, it finds an available
    Jibri instance and launches (or reuses) a container for that room.
    """

    def __init__(self):
        self.active_containers = {}  # room -> container_name

    def start_recording(self, room, session_id):
        """
        Launch a recording for the given room.
        Uses the same jitsi/jibri:unstable image with --entrypoint and
        JIBRI_INSTANCE_ID env to signal it's a dynamic instance.
        """
        container_name = f"jibri-ondemand-{session_id[:8]}"
        log.info(f"Starting Jibri container '{container_name}' for room: {room}")

        # Build docker run command matching the jibri-pool.yml config
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            f"--network={JITSI_NETWORK}",
            "--shm-size=2gb",
            "--cap-add=SYS_ADMIN",
            "-e", f"JIBRI_INSTANCE_ID=ondemand-{session_id[:8]}",
            "-e", "TZ=UTC",
            "-v", f"{CONFIG_DIR}/jibri-1:/config:Z",
            "-v", f"{RECORDINGS_DIR}:/recordings:Z",
            JIBRI_IMAGE,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                container_id = result.stdout.strip()
                self.active_containers[room] = container_name
                log.info(f"Container '{container_name}' started: {container_id}")
            else:
                log.error(f"Failed to start container: {result.stderr}")
        except subprocess.TimeoutExpired:
            log.error("Timeout starting container")
        except Exception as e:
            log.error(f"Error starting container: {e}")

    def stop_recording(self, room, session_id):
        """Stop a recording container for the given room."""
        container_name = self.active_containers.pop(room, None)
        if not container_name:
            log.warning(f"No active container for room: {room}")
            return

        log.info(f"Stopping container '{container_name}'")
        try:
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True, timeout=30
            )
            subprocess.run(
                ["docker", "rm", container_name],
                capture_output=True, timeout=15
            )
            log.info(f"Container '{container_name}' stopped and removed")
        except Exception as e:
            log.error(f"Error stopping container: {e}")


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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Load password from env or .env.jibri
    password = os.environ.get("JIBRI_XMPP_PASSWORD", "")
    if not password:
        for p in ["/app/.env.jibri", "/config/.env.jibri",
                   os.path.expanduser("~/.jitsi-meet-cfg/.env.jibri"),
                   ".env.jibri"]:
            env = load_env(p)
            password = env.get("JIBRI_XMPP_PASSWORD", "")
            if password:
                break

    if not password:
        log.error("JIBRI_XMPP_PASSWORD not found in env or .env.jibri")
        sys.exit(1)

    orchestrator = JibriOrchestrator()

    def on_trigger(room, session_id):
        orchestrator.start_recording(room, session_id)

    def signal_handler(signum, frame):
        log.info(f"Signal {signum} received, shutting down...")
        if xmpp:
            xmpp.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Main loop with reconnection
    reconnect_delay = 1
    xmpp = None

    while True:
        try:
            xmpp = XMPP(JID, password, on_trigger)

            if xmpp.connect():
                reconnect_delay = 1  # reset on success
                log.info("LightRec v3: Connected. Waiting for JibriIq triggers...")
                xmpp.listen()
            else:
                log.error("Connection failed")

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Unexpected error: {e}")

        if not xmpp or not xmpp.running:
            # Reconnection
            log.info(f"Reconnecting in {reconnect_delay}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)
        else:
            break

    if xmpp:
        xmpp.disconnect()


if __name__ == "__main__":
    main()
