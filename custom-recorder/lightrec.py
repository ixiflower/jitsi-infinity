#!/usr/bin/env python3
"""
LightRec v3 — Native Jitsi Recorder.
Connects to brewery as a Jibri instance, receives recording triggers,
records the conference using FFmpeg directly. No Jibri containers needed.
"""
import base64
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
RECORDINGS_DIR = os.environ.get("RECORDINGS_DIR", "/recordings")
JIBRI_USER = os.environ.get("JIBRI_XMPP_USER", "jibri")
JIBRI_DOMAIN = os.environ.get("JIBRI_XMPP_DOMAIN", "auth.meet.jitsi")
JID = f"{JIBRI_USER}@{JIBRI_DOMAIN}"
XMPP_HOST = os.environ.get("XMPP_SERVER", "xmpp.meet.jitsi")
XMPP_PORT = int(os.environ.get("XMPP_PORT", "5222"))
BREWERY_MUC = os.environ.get("JIBRI_BREWERY_MUC", "jibribrewery@internal-muc.meet.jitsi")
# The stream:stream to attribute must match prosody's virtual host, not the DNS name
XMPP_VHOST = "auth.meet.jitsi"
MAX_RECONNECT_DELAY = 30


class Recorder:
    """Manages a single FFmpeg recording process per room."""

    def __init__(self, recordings_dir):
        self.recordings_dir = Path(recordings_dir)
        try:
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback = Path("/tmp/recordings")
            log.warning(f"Cannot write to {recordings_dir}, using {fallback}")
            self.recordings_dir = fallback
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.active = {}  # session_id -> dict with process info
        self._busy = False

    @property
    def is_busy(self):
        return self._busy

    def start(self, room, session_id, muc_domain="muc.meet.jitsi"):
        """Start recording the given room with FFmpeg (silence fallback)."""
        if session_id in self.active:
            log.warning(f"Session {session_id} already active, skipping")
            return False

        room_name = room.split("@")[0] if "@" in room else room

        output_file = self.recordings_dir / f"{room_name}_{int(time.time())}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", "1",
            "-c:a", "aac",
            str(output_file),
        ]

        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 6/10: Starting silence FFmpeg")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Room: {room_name}")
        log.info(f"  Session: {session_id[:12]}")
        log.info(f"  Output: {output_file}")
        log.info(f"  Command: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            log.error(f"  ❌ ffmpeg not found at /usr/local/bin/ffmpeg")
            log.error(f"  Install ffmpeg or check PATH")
            return False
        except Exception as e:
            log.error(f"  ❌ Failed to start FFmpeg: {e}")
            return False

        self.active[session_id] = {
            "room": room,
            "output": output_file,
            "proc": proc,
            "started": time.time(),
            "sdp": None,
        }
        log.info(f"  ✅ Silence FFmpeg running (pid={proc.pid})")
        log.info(f"  Recording started for room '{room_name}' [{session_id[:8]}] → {output_file.name}")
        self._busy = True
        return True

    def stop(self, session_id=None, room=None):
        """Stop a running recording and clean up."""
        session_ids_to_remove = []
        if session_id and session_id in self.active:
            session_ids_to_remove = [session_id]
        elif room:
            for sid, rec in list(self.active.items()):
                if rec.get("room") == room:
                    session_ids_to_remove.append(sid)
        else:
            session_ids_to_remove = list(self.active.keys())

        for sid in session_ids_to_remove:
            info = self.active.pop(sid, None)
            if info:
                proc = info.get("proc")
                if proc:
                    log.info(f"  Terminating FFmpeg (pid={proc.pid})...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=2)
                sdp = info.get("sdp")
                if sdp and sdp.exists():
                    sdp.unlink(missing_ok=True)
                log.info(f"  ✅ Recording stopped: {info['output'].name}")
        self._busy = bool(self.active)
        return len(session_ids_to_remove) > 0

    # ── Video support ──────────────────────────────────────────────────

    def _extract_content_transport(self, stanza, content_name):
        """Extract ip and port from a Jingle content element by name.

        Returns (ip, port, dtls_fingerprint) or (None, None, None).
        """
        pattern = rf'<content\s+name=[\'"]{content_name}[\'"].*?</content>'
        m = re.search(pattern, stanza, re.DOTALL)
        if not m:
            return None, None, None
        content_xml = m.group(0)
        ip = self._xml_attr(content_xml, "ip")
        port = self._xml_attr(content_xml, "port")
        fingerprint = self._xml_attr(content_xml, "hash")
        return ip, port, fingerprint

    def upgrade_to_rtp(self, session_id, ip, port, room=None, dtls_fingerprint=None,
                       video_ip=None, video_port=None):
        """Upgrade an ongoing silence recording to real RTP capture
        once colibri channel info arrives from Jicofo."""
        info = self.active.get(session_id)
        if not info and room:
            # Try looking up by room JID (Jingle sid != Jibri session_id)
            for sid, rec in self.active.items():
                if rec.get("room") == room:
                    info = rec
                    session_id = sid
                    log.info(f"  Found session by room ({room}): sid={sid[:12]}")
                    break
        if not info:
            log.warning(f"  ❌ No active session {session_id[:8]} to upgrade")
            return False

        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 7/10: Upgrading silence → RTP")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Session: {session_id[:12]}")
        log.info(f"  Audio RTP target: {ip}:{port}")
        if video_ip and video_port:
            log.info(f"  Video RTP target: {video_ip}:{video_port}")
        else:
            log.info(f"  No video transport — audio only")
        if dtls_fingerprint:
            log.info(f"  DTLS fingerprint present")

        # Kill the silence FFmpeg process
        proc = info["proc"]
        if proc:
            log.info(f"  Killing silence FFmpeg (pid={proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=3)
                log.info(f"  ✅ Silence FFmpeg terminated")
            except subprocess.TimeoutExpired:
                log.warning(f"  Force-killing silence FFmpeg...")
                proc.kill()
                proc.wait(timeout=2)
                log.info(f"  ✅ Silence FFmpeg force-killed")

        # Build SDP for real RTP capture (audio + video)
        room_name = info["room"].split("@")[0] if "@" in info["room"] else info["room"]
        sdp_path = self.recordings_dir / f"{room_name}_colibri.sdp"
        output_path = info["output"]  # reuse same output file (overwrite silence)

        sdp_lines = [
            "v=0",
            f"o=- 0 0 IN IP4 {ip}",
            "s=Jitsi Recording",
            f"c=IN IP4 {ip}",
            "t=0 0",
            # Audio media line
            f"m=audio {port} RTP/AVP 111 0 8 9",
            "a=rtpmap:111 opus/48000/2",
            "a=rtpmap:0 PCMU/8000",
            "a=rtpmap:8 PCMA/8000",
            "a=rtpmap:9 G722/8000",
            "a=recvonly",
        ]
        # Video media line (if we have a RTP port)
        if video_ip and video_port:
            sdp_lines += [
                f"m=video {video_port} RTP/AVP 100 41",
                "a=rtpmap:100 VP8/90000",
                "a=rtpmap:41 AV1/90000",
                f"c=IN IP4 {video_ip}",
                "a=recvonly",
            ]

        sdp_content = "\n".join(sdp_lines) + "\n"
        sdp_path.write_text(sdp_content)
        log.info(f"  ✅ SDP written to {sdp_path}")
        log.info(f"  SDP content:\n{sdp_content.strip()}")

        # Restart FFmpeg with RTP input (audio + video)
        cmd = [
            "ffmpeg", "-y",
            "-protocol_whitelist", "file,udp,rtp,tcp",
            "-i", str(sdp_path),
            "-c:a", "aac",
            "-b:a", "128k",
        ]
        if video_ip and video_port:
            # Include video stream
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
        else:
            # Audio only
            cmd += ["-vn"]
        cmd.append(str(output_path))

        log.info(f"  Starting RTP FFmpeg: {' '.join(cmd)}")

        try:
            new_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            log.error(f"  ❌ ffmpeg not found! Cannot record RTP stream")
            log.error(f"  Recording will remain as silence")
            info["proc"] = None
            info["sdp"] = sdp_path
            return False
        except Exception as e:
            log.error(f"  ❌ Failed to start RTP FFmpeg: {e}")
            info["proc"] = None
            info["sdp"] = sdp_path
            return False

        info["proc"] = new_proc
        info["sdp"] = sdp_path

        label = "audio+video" if video_ip and video_port else "audio"
        log.info(f"  Recording upgraded to RTP ({label}) for {info['room']} → {ip}:{port}")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  ✅ RTP upgrade successful — recording real media!")
        return True


class LightRec:
    """XMPP bot that sits in the Jibri brewery and handles recording triggers."""

    def __init__(self, jid, password, recordings_dir="/recordings",
                 brewery_muc=BREWERY_MUC, server=XMPP_HOST, port=XMPP_PORT):
        self.jid = jid
        self.password = password
        self.brewery_muc = brewery_muc
        self.server = server
        self.port = port
        self.resource = f"jibri-{uuid.uuid4().hex[:8]}"
        self.full_jid = f"{jid}/{self.resource}"

        self.recorder = Recorder(recordings_dir)
        self.triggering = None  # Track active trigger for stop handling
        self.running = True

        # Callbacks (set by main loop)
        self.on_trigger = None
        self.on_colibri = None

        # XMPP state
        self._xmpp_sock = None
        self._xmpp_buf = b""
        self._stream_id = None
        self._log_sid = None
        self._xmpp_recv_thread = None

    # ── Low-level XMPP ─────────────────────────────────────────────────

    def _recv_xmpp(self, timeout=300):
        """Read one complete XMPP stanza from the socket buffer.
        Handles stream headers (<stream:stream...>), normal stanzas
        (<iq>, <presence>, <message>), and stream features
        (<stream:features>...features...</stream:features>)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            # 1) Stream header: <stream:stream ...> (self-opening, no closing tag)
            if self._xmpp_buf[:1] == b"<" or b"\n<stream:" in self._xmpp_buf:
                stream_idx = self._xmpp_buf.find(b"<stream:stream")
                if stream_idx >= 0:
                    end_open = self._xmpp_buf.find(b">", stream_idx)
                    if end_open >= 0:
                        stanza = self._xmpp_buf[:end_open + 1]
                        self._xmpp_buf = self._xmpp_buf[end_open + 1:]
                        return stanza

            # 2) Stream features: <stream:features>...</stream:features>
            feat_open = self._xmpp_buf.find(b"<stream:features>")
            if feat_open >= 0:
                feat_close = self._xmpp_buf.find(b"</stream:features>")
                if feat_close >= 0:
                    full = self._xmpp_buf[:feat_close + len(b"</stream:features>")]
                    self._xmpp_buf = self._xmpp_buf[feat_close + len(b"</stream:features>"):]
                    return full

            # 3) Normal stanzas: <iq>, <presence>, <message>, <auth>, etc.
            #    Look for a top-level opening tag and its matching close
            for opener in [b"<iq ", b"<presence", b"<message ", b"<auth ", b"<success", b"<failure",
                           b"<proceed", b"<challenge", b"<response", b"<bind", b"<query",
                           b"<starttls", b"<store", b"<x "]:
                open_idx = self._xmpp_buf.find(opener)
                if open_idx < 0:
                    continue
                # Self-closing? <foo .../>
                close_self = self._xmpp_buf.find(b"/>", open_idx)
                next_open = self._xmpp_buf.find(b"<", open_idx + 1)
                if close_self >= 0 and (next_open < 0 or close_self < next_open):
                    stanza = self._xmpp_buf[:close_self + 2]
                    self._xmpp_buf = self._xmpp_buf[close_self + 2:]
                    return stanza
                # With closing tag: <foo ...>...</foo>
                # Find the tag name
                tag_end = self._xmpp_buf.find(b" ", open_idx + 1)
                if tag_end < 0 or tag_end > open_idx + 30:
                    tag_end = self._xmpp_buf.find(b">", open_idx + 1)
                tag_name_end = tag_end if self._xmpp_buf[tag_end:tag_end+1] == b">" else -1
                if tag_name_end < 0:
                    # <foo attr...>
                    gt = self._xmpp_buf.find(b">", open_idx)
                    if gt < 0:
                        continue
                    # Get tag name
                    space_or_gt = self._xmpp_buf.find(b" ", open_idx)
                    close_gt = self._xmpp_buf.find(b">", open_idx)
                    if space_or_gt < 0 or space_or_gt > close_gt:
                        name_end = close_gt
                    else:
                        name_end = space_or_gt
                    tag_name = self._xmpp_buf[open_idx + 1:name_end]
                    # Find matching closing tag
                    close_tag = b"</" + tag_name + b">"
                    close_idx = self._xmpp_buf.find(close_tag, open_idx + 1)
                    if close_idx >= 0:
                        stanza = self._xmpp_buf[:close_idx + len(close_tag)]
                        self._xmpp_buf = self._xmpp_buf[close_idx + len(close_tag):]
                        return stanza

            # 4) Read more data
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self._xmpp_sock.settimeout(min(remaining, 5))
                chunk = self._xmpp_sock.recv(65536)
                if not chunk:
                    log.warning("XMPP socket closed by peer")
                    return None
                self._xmpp_buf += chunk
            except socket.timeout:
                continue
            except Exception as e:
                log.error(f"XMPP recv error: {e}")
                return None
        return None

    def _send_xmpp(self, data):
        raw = data.encode() if isinstance(data, str) else data
        try:
            self._xmpp_sock.sendall(raw)
            return True
        except Exception as e:
            log.error(f"XMPP send error: {e}")
            return False

    def _wait_for(self, tag_pattern, timeout=30):
        """Read stanzas until one matching tag_pattern arrives."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            stanza = self._recv_xmpp(timeout=min(10, deadline - time.time()))
            if stanza is None:
                return None
            if tag_pattern in stanza:
                return stanza
        log.warning(f"Timeout waiting for {tag_pattern}")
        return None

    # ── Connection & Auth ──────────────────────────────────────────────

    def connect(self):
        """Open TCP + TLS to XMPP server."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 1/10: Connecting to XMPP server")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Server: {self.server}:{self.port}")
        self._xmpp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._xmpp_sock.settimeout(10)
        try:
            self._xmpp_sock.connect((self.server, self.port))
        except Exception as e:
            log.error(f"  ❌ Connection failed: {e}")
            return False

        # Start TLS
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 2/10: Starting TLS")
        log.info(f"══════════════════════════════════════════")
        # Send initial stream header (client must open the XML stream first)
        self._send_xmpp(
            f'<stream:stream to="{XMPP_VHOST}" xmlns="jabber:client" '
            f'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
        )
        # Wait for server's stream header
        stanza = self._recv_xmpp(timeout=10)
        if stanza is None:
            log.error("  ❌ No stream header received")
            return False
        log.info(f"  ✅ TCP/Stream connection established")

        # Read stream features (the server sent them in the same TCP packet)
        features = self._recv_xmpp(timeout=3)
        if features:
            log.info(f"  Server features: {features[:200].decode(errors='replace')}")
        else:
            log.info("  No features received yet")

        self._send_xmpp(
            f'<starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>'
        )
        resp = self._wait_for(b"<proceed", timeout=10)
        if resp is None:
            log.error("  ❌ TLS not offered")
            return False
        log.info(f"  ✅ TLS negotiation initiated")

        # Wrap socket
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            self._xmpp_sock = context.wrap_socket(
                self._xmpp_sock, server_hostname=self.server
            )
        except Exception as e:
            log.error(f"  ❌ TLS handshake failed: {e}")
            return False
        log.info(f"  ✅ TLS established")

        # Restart stream
        self._send_xmpp(
            f'<stream:stream to="{XMPP_VHOST}" xmlns="jabber:client" '
            f'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
        )
        stanza = self._recv_xmpp(timeout=10)
        if stanza is None:
            log.error("  ❌ No post-TLS stream header")
            return False

        # Extract stream ID
        m = re.search(rb"id=['\"]([^'\"]+)['\"]", stanza)
        self._stream_id = m.group(1).decode() if m else "unknown"
        log.info(f"  ✅ TLS established (stream ID: {self._stream_id})")
        return True

    def authenticate(self):
        """SASL PLAIN auth."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 3/10: Authenticating (SASL PLAIN)")
        log.info(f"══════════════════════════════════════════")

        # Extract user and domain
        user, domain = self.jid.split("@", 1)
        auth_str = f"\x00{user}\x00{self.password}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        self._send_xmpp(
            f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">'
            f'{auth_b64}</auth>'
        )
        resp = self._wait_for(b"<success", timeout=10)
        if resp is None:
            log.error("  ❌ SASL auth failed — no success response")
            return False
        log.info(f"  ✅ SASL authenticated as {self.jid}")

        # Restart stream after auth
        self._send_xmpp(
            f'<stream:stream to="{XMPP_VHOST}" xmlns="jabber:client" '
            f'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
        )
        stanza = self._recv_xmpp(timeout=10)
        if stanza is None:
            log.error("  ❌ No post-auth stream header")
            return False
        return True

    # ── Resource Binding ───────────────────────────────────────────────

    def bind_resource(self):
        """Bind the XMPP resource."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 4/10: Binding resource")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Resource: {self.resource}")
        self._send_xmpp(
            f'<iq type="set" id="bind_1">'
            f'<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind">'
            f'<resource>{self.resource}</resource>'
            f'</bind>'
            f'</iq>'
        )
        resp = self._wait_for(b"<iq", timeout=10)
        if resp is None or b"type='result'" not in resp:
            log.error(f"  ❌ Resource binding failed")
            return False
        log.info(f"  ✅ Bound as {self.full_jid}")
        return True

    # ── Brewery MUC ────────────────────────────────────────────────────

    def join_brewery(self):
        """Join the Jibri brewery MUC and announce capabilities."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 5/10: Joining brewery MUC")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Brewery: {self.brewery_muc}")

        # Send presence with jibri status
        presence = (
            f'<presence to="{self.brewery_muc}/{self.resource}" xmlns="jabber:client">'
            f'<x xmlns="http://jabber.org/protocol/muc"/>'
            f'<jibri xmlns="http://jitsi.org/protocol/jibri">'
            f'<status>idle</status>'
            f'<capabilities>'
            f'<capability>recording</capability>'
            f'</capabilities>'
            f'</jibri>'
            f'</presence>'
        )
        self._send_xmpp(presence)

        # Wait for room join
        resp = self._wait_for(b"xmlns='http://jabber.org/protocol/muc#user'", timeout=15)
        if resp is None:
            log.warning("  ⚠ No MUC join confirmation (non-fatal)")
        log.info(f"  ✅ Brewery MUC joined: {self.brewery_muc}")
        return True

    # ── Message Handling ───────────────────────────────────────────────

    def _handle_stanza(self, stanza):
        """Route incoming stanzas to the right handler."""
        if b"<iq " in stanza and b"type='result'" in stanza:
            return  # Ignore IQ results
        if b"<iq " in stanza and (b"jibribrewery" in stanza or b"jibri" in stanza):
            if b"<jibri" in stanza or b"JibriIq" in stanza:
                self._handle_jibri_iq(stanza)
            else:
                self._handle_colibri_iq(stanza.decode("utf-8", errors="replace"))
            return
        if b"<presence" in stanza:
            if b"/focus" in stanza:
                self._handle_colibri_iq(stanza.decode("utf-8", errors="replace"))
            return
        if b"<message" in stanza:
            self._handle_message(stanza)
            return
        if b"<iq " in stanza and b"type='get'" in stanza:
            # Respond to pings / disco
            self._handle_iq_get(stanza)

    def _handle_message(self, stanza):
        """Handle incoming message stanzas."""
        # Extract body if present
        m = re.search(rb"<body>(.*?)</body>", stanza, re.DOTALL)
        if m:
            log.info(f"  Message: {m.group(1).decode('utf-8', errors='replace')[:200]}")

    def _handle_iq_get(self, stanza):
        """Handle IQ get stanzas (disco info, ping, etc.)."""
        stanza_str = stanza.decode("utf-8", errors="replace")
        m = re.search(rb"id=['\"]([^'\"]+)['\"]", stanza)
        iq_id = m.group(1).decode() if m else "unknown"

        # Disco info
        if b"query" in stanza and b"info" in stanza:
            log.info(f"  Handling disco#info: {iq_id}")
            resp = (
                f'<iq type="result" id="{iq_id}" to="{self.brewery_muc}" from="{self.full_jid}">'
                f'<query xmlns="http://jabber.org/protocol/disco#info">'
                f'<identity category="client" type="jibri" name="LightRec v3"/>'
                f'<feature var="http://jabber.org/protocol/disco#info"/>'
                f'</query></iq>'
            )
            self._send_xmpp(resp)

        # Ping
        if b"ping" in stanza:
            log.info(f"  Handling ping: {iq_id}")
            resp = (
                f'<iq type="result" id="{iq_id}" to="{self.brewery_muc}" '
                f'from="{self.full_jid}"/>'
            )
            self._send_xmpp(resp)

    def _handle_jibri_iq(self, stanza_raw):
        """Handle a JibriIq from the brewery (recording start/stop)."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"=== JibriIq RECEIVED (Brewery) ===")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  Raw: {stanza_raw[:500]}")

        stanza = stanza_raw.decode("utf-8", errors="replace")

        # Extract attributes
        def attr(name):
            m = re.search(rf'{name}=[\'"]([^\'"]+)[\'"]', stanza)
            return m.group(1) if m else None

        session_id = None
        room = None
        action = None

        # Try to find JibriIq XML content
        m = re.search(r'<jibri[^>]*xmlns=[\'"]http://jitsi\.org/protocol/jibri[\'"]', stanza)
        if m:
            # Find the rest after xmlns
            log.info(f"  Found jibri namespace")
            action_m = re.search(r'<action>([^<]+)</action>', stanza)
            if action_m:
                action = action_m.group(1)
            room_m = re.search(r'<room[^>]*>([^<]+)</room>', stanza)
            if room_m:
                room = room_m.group(1)
            sid_m = re.search(r'<sessionid[^>]*>([^<]+)</sessionid>', stanza)
            if sid_m:
                session_id = sid_m.group(1)
        else:
            # Fallback: try regex scanning
            action = re.search(r'<action[^>]*>([^<]+)</action>', stanza)
            action = action.group(1) if action else None
            room = re.search(r'<room[^>]*>([^<]+)</room>', stanza)
            room = room.group(1) if room else None
            session_id = re.search(r'<sessionid[^>]*>([^<]+)</sessionid>', stanza)
            session_id = session_id.group(1) if session_id else None

        if not session_id:
            # Generate a session_id for stop detection
            session_id = f"unknown-{uuid.uuid4().hex[:8]}"

        log.info(f"  Action: {action}")
        log.info(f"  Room: {room}")
        log.info(f"  Session: {session_id}")

        # Send ACK
        self._send_xmpp(
            f'<iq type="result" id="{attr("id") or "unknown"}" '
            f'to="{attr("from") or self.brewery_muc}" '
            f'from="{self.full_jid}"/>'
        )
        log.info(f"  ✅ ACK sent")

        if action == "start" and room:
            # Mark as triggering
            self.triggering = session_id
            log.info(f"  ⏩ Triggering: conference MUC join")
            self._join_room_muc(room)
            log.info(f"  ⏩ Starting recording pipeline...")
            if self.on_trigger:
                self.on_trigger(room, session_id)
        elif action == "stop":
            log.info(f"  STOP requested — leaving room & stopping FFmpeg")
            # Leave the conference room MUC
            self._leave_room_muc(room)
            if self.on_trigger:
                self.on_trigger(room, session_id, action="stop")
            log.info(f"  ✅ Recording stopped")
        else:
            log.warning(f"  ⚠ Unknown action: {action}")
        log.info(f"══════════════════════════════════════════")

    def _join_room_muc(self, room):
        """Join the conference room MUC as a recording participant."""
        log.info(f"  Joining conference MUC: {room}")
        nick = f"recorder_{self.resource.split('-')[-1]}"
        presence = (
            f'<presence to="{room}/{nick}" xmlns="jabber:client">'
            f'<x xmlns="http://jabber.org/protocol/muc"/>'
            f'</presence>'
        )
        self._send_xmpp(presence)
        log.info(f"  ✅ Conference MUC joined as {nick}")

    def _leave_room_muc(self, room):
        """Leave a conference room MUC."""
        if not room:
            return
        nick = f"recorder_{self.resource.split('-')[-1]}"
        log.info(f"  Leaving conference MUC: {room}")
        presence = (
            f'<presence to="{room}/{nick}" type="unavailable" xmlns="jabber:client">'
            f'<x xmlns="http://jabber.org/protocol/muc"/>'
            f'</presence>'
        )
        self._send_xmpp(presence)
        log.info(f"  ✅ Left conference MUC")

    def _handle_colibri_iq(self, stanza):
        """Handle colibri/jingle IQ stanzas containing transport info
        (RTP port, IP, SRTP key) from Jicofo via JVB.

        Supports both audio and video transport extraction.
        """
        try:
            log.info(f"══════════════════════════════════════════")
            log.info(f"  STEP 8/10: Colibri IQ received from JVB")
            log.info(f"══════════════════════════════════════════")

            # Extract Jingle session ID
            sid = self._xml_attr(stanza, "sid")
            # Extract the room from the stanza's from attribute
            iq_from = self._xml_attr(stanza, "from")
            room_jid = None
            if iq_from and "@" in iq_from:
                room_jid = iq_from.split("/")[0] if "/" in iq_from else iq_from
            # Extract transport candidate info (first = audio)
            ip = self._xml_attr(stanza, "ip")
            port = self._xml_attr(stanza, "port")
            srtp_key = self._xml_attr(stanza, "srtp-key-context")
            ufrag = self._xml_attr(stanza, "ufrag")
            pwd = self._xml_attr(stanza, "pwd")

            # Extract video transport from <content name='video'> section
            video_ip = None
            video_port = None
            if "/focus" in (iq_from or ""):
                video_ip, video_port, _ = self.recorder._extract_content_transport(stanza, "video")
                if video_port:
                    log.info(f"  📹 Video channel: {video_ip}:{video_port}")

            log.info(f"  sid={sid} audio={ip}:{port} video={video_ip}:{video_port}")
            # Only process JVB candidates (from Jicofo focus, not P2P users)
            is_jvb = iq_from and "/focus" in iq_from
            if ip and port:
                if is_jvb:
                    log.info(f"  ✅ RTP audio channel allocated: {ip}:{port}")
                else:
                    log.info(f"  ⚠ Skipping P2P candidate ({ip}:{port}) — waiting for JVB")
                    ip = None  # don't upgrade from P2P
            if srtp_key:
                log.info(f"  SRTP key: present ({len(srtp_key)} chars)")
            if ufrag:
                log.info(f"  ICE: ufrag={ufrag} pwd={'present' if pwd else 'none'}")

            # If we have an active recording and received JVB colibri transport,
            # upgrade the recording from silence to real RTP (audio + video)
            if sid and ip and port and self.on_colibri and is_jvb:
                log.info(f"  ⏩ Upgrading recording to RTP...")
                self.on_colibri(sid, ip, port, room_jid, srtp_key,
                                video_ip=video_ip, video_port=video_port)
            else:
                missing = []
                if not sid: missing.append("sid")
                if not ip: missing.append("ip")
                if not port: missing.append("port")
                log.warning(f"  ⚠ Incomplete colibri info, missing: {', '.join(missing)}")
        except Exception as e:
            log.error(f"  ❌ Error handling colibri IQ: {e}")
            import traceback
            log.error(traceback.format_exc())

    def _xml_attr(self, xml_str, attr):
        m = re.search(rf'{attr}=["\']([^"\']+)["\']', xml_str)
        return m.group(1) if m else None

    def _send(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self._send_xmpp(data)

    # ── Main Loop ──────────────────────────────────────────────────────

    def listen(self):
        """Read stanzas in a loop, dispatching to handlers."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 10/10: Listening for recording triggers")
        log.info(f"══════════════════════════════════════════")
        log.info(f"LightRec v3: Ready for recording triggers")

        while self.running:
            try:
                stanza = self._recv_xmpp(timeout=60)
                if stanza is None:
                    log.info("No stanzas received (timeout) — still alive")
                    continue
                self._handle_stanza(stanza)
            except Exception as e:
                log.error(f"Listen loop error: {e}")
                import traceback
                log.error(traceback.format_exc())
                break

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        # Stop all recordings
        self.recorder.stop()
        # Send unavailable presence
        self._send_xmpp(
            f'<presence type="unavailable" xmlns="jabber:client"/>'
        )
        # Close XMPP stream
        self._send_xmpp("</stream:stream>")
        if self._xmpp_sock:
            try:
                self._xmpp_sock.close()
            except Exception:
                pass


# ── Main Entry Point ──────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-5s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    jid = os.environ.get("JIBRI_XMPP_USER", "jibri")
    domain = os.environ.get("JIBRI_XMPP_DOMAIN", "auth.meet.jitsi")
    password = os.environ.get("JIBRI_XMPP_PASSWORD", "jibri")
    full_jid = f"{jid}@{domain}"
    recordings_dir = os.environ.get("RECORDINGS_DIR", "/recordings")
    brewery_muc = os.environ.get("JIBRI_BREWERY_MUC", "jibribrewery@internal-muc.meet.jitsi")
    xmpp_host = os.environ.get("XMPP_SERVER", "xmpp.meet.jitsi")
    xmpp_port = int(os.environ.get("XMPP_PORT", "5222"))

    lightrec = LightRec(
        jid=full_jid,
        password=password,
        recordings_dir=recordings_dir,
        brewery_muc=brewery_muc,
        server=xmpp_host,
        port=xmpp_port,
    )

    # ── Recording callbacks ───────────────────────────────────────────
    def on_trigger(room, session_id, action="start"):
        """Handle recording start/stop from the brewery."""
        if action == "start":
            log.info(f"══════════════════════════════════════════")
            log.info(f"  RECORDER CALLBACK: on_trigger('start')")
            log.info(f"══════════════════════════════════════════")
            lightrec.recorder.start(room, session_id)
        elif action == "stop":
            log.info(f"══════════════════════════════════════════")
            log.info(f"  RECORDER CALLBACK: on_trigger('stop')")
            log.info(f"══════════════════════════════════════════")
            lightrec.recorder.stop(room=room)

    def on_colibri(sid, ip, port, room=None, srtp_key=None,
                   video_ip=None, video_port=None):
        """Called when colibri transport info arrives — upgrade recording
        from silence to real RTP with audio+video."""
        log.info(f"══════════════════════════════════════════")
        log.info(f"  STEP 9/10: Colibri callback — upgrading")
        log.info(f"══════════════════════════════════════════")
        log.info(f"  sid={sid} RTP {ip}:{port} room={room}")
        if video_ip and video_port:
            log.info(f"  video={video_ip}:{video_port}")
        lightrec.recorder.upgrade_to_rtp(sid, ip, port, room, srtp_key,
                                         video_ip=video_ip, video_port=video_port)

    lightrec.on_trigger = on_trigger
    lightrec.on_colibri = on_colibri

    # ── Connect ───────────────────────────────────────────────────────
    if not lightrec.connect():
        log.error("Failed to connect")
        sys.exit(1)

    if not lightrec.authenticate():
        log.error("Failed to authenticate")
        sys.exit(1)

    if not lightrec.bind_resource():
        log.error("Failed to bind resource")
        sys.exit(1)

    if not lightrec.join_brewery():
        log.error("Failed to join brewery")
        sys.exit(1)

    # ── Listen ────────────────────────────────────────────────────────
    try:
        lightrec.listen()
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        lightrec.stop()
        log.info("Goodbye.")


if __name__ == "__main__":
    main()
