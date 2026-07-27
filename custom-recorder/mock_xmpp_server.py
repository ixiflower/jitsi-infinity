#!/usr/bin/env python3
"""
Mock XMPP Server for local LightRec testing.

Simplified version with explicit timing and robust socket handling.
"""
import base64
import logging
import os
import socket
import ssl
import threading
import time
import uuid

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [MOCK] %(levelname)s %(message)s",
)
log = logging.getLogger("mock-xmpp")

HOST = "127.0.0.1"
PORT = 5222
CERT = "/tmp/mock_xmpp_cert.pem"
KEY = "/tmp/mock_xmpp_key.pem"
DOMAIN = "auth.meet.jitsi"
BREWERY = "jibribrewery@internal-muc.meet.jitsi"


class MockXmppServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self._stop = threading.Event()

    def _recv_stanza(self, conn, timeout=8):
        """Read one XML stanza from a plain socket, waiting up to timeout secs."""
        conn.settimeout(timeout)
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                log.warning("recv timed out")
                return None, buf
            except OSError as e:
                log.error(f"recv error: {e}")
                return None, buf
            if not chunk:
                log.info("Connection closed by peer")
                return None, buf
            buf += chunk
            # Try to extract a complete stanza
            # Look for stream:stream header
            if b"<stream:stream" in buf and b">" in buf:
                si = buf.find(b"<stream:stream")
                ei = buf.find(b">", si)
                if ei >= 0:
                    stanza = buf[:ei + 1]
                    rest = buf[ei + 1:]
                    log.debug(f"Got stream header ({len(stanza)}B)")
                    return stanza, rest
            # Look for complete XML stanza: <tag>...</tag> or <tag/>
            for tag in [b"<iq ", b"<presence", b"<message ", b"<starttls",
                        b"<auth ", b"<success", b"<failure",
                        b"<proceed"]:
                if tag not in buf:
                    continue
                si = buf.find(tag)
                # Find matching close or self-close
                if b"/>" in buf[si:]:
                    # Self-closing
                    if b"<proceed" in tag or b"<success" in tag or b"<failure" in tag:
                        # These are not XML, just tags
                        ei = buf.find(b">", si)
                        stanza = buf[:ei + 1]
                        rest = buf[ei + 1:]
                        return stanza, rest
                # Standard XML: find </tag>
                tag_name = tag[1:].split(b" ")[0].split(b">")[0]
                close_tag = b"</" + tag_name + b">"
                if close_tag in buf[si:]:
                    ei = buf.find(close_tag, si) + len(close_tag)
                    stanza = buf[:ei]
                    rest = buf[ei:]
                    return stanza, rest
        return None, buf

    def handle_client(self, conn, addr):
        log.info(f"Client connected: {addr}")
        resource = None
        buf = b""

        def send(data, label=""):
            if isinstance(data, str):
                data = data.encode()
            log.info(f"SEND [{label}] ({len(data)}B)")
            conn.sendall(data)
            log.info(f"SEND [{label}] DONE")

        try:
            # ═══ STEP 1: Read client stream header ═══
            stanza, buf = self._recv_stanza(conn, timeout=8)
            if not stanza or b"stream:stream" not in stanza:
                log.error(f"Expected stream header, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received client stream header")

            # ═══ STEP 2: Send server stream header + features ═══
            sid = uuid.uuid4().hex[:8]
            # Send everything in ONE write to avoid TCP coalescing issues
            payload = (
                f"<?xml version='1.0'?>"
                f"<stream:stream from='{DOMAIN}' id='{sid}' "
                f"xmlns='jabber:client' "
                f"xmlns:stream='http://etherx.jabber.org/streams' "
                f"version='1.0'>"
                f"<stream:features>"
                f"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>"
                f"</stream:features>"
            )
            send(payload, "stream+features")
            time.sleep(0.1)

            # ═══ STEP 3: Read STARTTLS ═══
            stanza, buf = self._recv_stanza(conn, timeout=5)
            if not stanza or b"starttls" not in stanza:
                log.error(f"Expected STARTTLS, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received STARTTLS")

            # ═══ STEP 4: Send proceed + wrap TLS ═══
            send("<proceed xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>", "proceed")
            log.info("Sent proceed, wrapping TLS...")

            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(CERT, KEY)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = context.wrap_socket(conn, server_side=True)
            conn.settimeout(8)
            buf = b""
            log.info("✓ TLS established")

            # ═══ STEP 5: Read post-TLS stream header ═══
            stanza, buf = self._recv_stanza(conn, timeout=8)
            if not stanza or b"stream:stream" not in stanza:
                log.error(f"Expected post-TLS stream, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received post-TLS stream header")

            # ═══ STEP 6: Send post-TLS stream + SASL features ═══
            sid2 = uuid.uuid4().hex[:8]
            payload = (
                f"<?xml version='1.0'?>"
                f"<stream:stream from='{DOMAIN}' id='{sid2}' "
                f"xmlns='jabber:client' "
                f"xmlns:stream='http://etherx.jabber.org/streams' "
                f"version='1.0'>"
                f"<stream:features>"
                f"<mechanisms xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>"
                f"<mechanism>PLAIN</mechanism>"
                f"</mechanisms>"
                f"</stream:features>"
            )
            send(payload, "post-tls+features")
            time.sleep(0.1)

            # ═══ STEP 7: Read SASL auth ═══
            stanza, buf = self._recv_stanza(conn, timeout=5)
            if not stanza or b"auth" not in stanza:
                log.error(f"Expected SASL auth, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received SASL auth")

            # ═══ STEP 8: Send auth success ═══
            send("<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>", "auth-ok")
            time.sleep(0.1)

            # ═══ STEP 9: Read post-auth stream header ═══
            buf = b""
            stanza, buf = self._recv_stanza(conn, timeout=8)
            if not stanza or b"stream:stream" not in stanza:
                log.error(f"Expected post-auth stream, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received post-auth stream header")

            # ═══ STEP 10: Send post-auth stream + bind/session features ═══
            sid3 = uuid.uuid4().hex[:8]
            payload = (
                f"<?xml version='1.0'?>"
                f"<stream:stream from='{DOMAIN}' id='{sid3}' "
                f"xmlns='jabber:client' "
                f"xmlns:stream='http://etherx.jabber.org/streams' "
                f"version='1.0'>"
                f"<stream:features>"
                f"<bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>"
                f"<session xmlns='urn:ietf:params:xml:ns:xmpp-session'/>"
                f"</stream:features>"
            )
            send(payload, "post-auth+features")
            time.sleep(0.1)

            # ═══ STEP 11: Read IQ bind ═══
            stanza, buf = self._recv_stanza(conn, timeout=5)
            if not stanza or b"bind" not in stanza:
                log.error(f"Expected IQ bind, got: {stanza[:80] if stanza else None}")
                return
            log.info("✓ Received IQ bind")

            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(stanza)
                ns = "{urn:ietf:params:xml:ns:xmpp-bind}"
                res_el = root.find(f".//{ns}resource")
                resource = res_el.text if res_el is not None else "lightrec"
            except Exception:
                resource = "lightrec"

            iq_id = stanza.split(b"id='")[1].split(b"'")[0].decode() if b"id='" in stanza else "bind-1"
            full_jid = f"jibri@{DOMAIN}/{resource}"

            send(
                f"<iq type='result' id='{iq_id}'>"
                f"<bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'>"
                f"<jid>{full_jid}</jid>"
                f"</bind></iq>",
                "bind-result"
            )
            log.info(f"✓ Bound: {full_jid}")

            # ═══ STEP 12: Read IQ session ═══
            stanza, buf = self._recv_stanza(conn, timeout=5)
            if stanza and b"session" in stanza:
                sid_id = stanza.split(b"id='")[1].split(b"'")[0].decode() if b"id='" in stanza else "sess-1"
                send(f"<iq type='result' id='{sid_id}'/>", "session-ok")
                log.info("✓ Session started")
            else:
                log.warning(f"Expected session, got: {stanza[:60] if stanza else None}")

            # ═══ STEP 13: Read brewery presence ═══
            stanza, buf = self._recv_stanza(conn, timeout=5)
            if stanza and b"presence" in stanza and b"muc" in stanza:
                log.info("✓ Received brewery MUC presence")
            else:
                log.warning(f"Expected brewery presence, got: {stanza[:60] if stanza else None}")

            # Send MUC self-presence
            send(
                f"<presence from='{BREWERY}/{resource}' to='{full_jid}'>"
                f"<x xmlns='http://jabber.org/protocol/muc'/></presence>",
                "muc-self"
            )

            time.sleep(0.5)
            log.info("=" * 50)
            log.info("LightRec connected to brewery! Ready for test scenario")
            log.info("=" * 50)

            # ════════════════════════════════════════════════════════════
            # TEST SCENARIO
            # ════════════════════════════════════════════════════════════

            test_room = "testroom@muc.meet.jitsi"
            test_sid = uuid.uuid4().hex

            # --- JibriIq START ---
            log.info(">>> JibriIq START")
            send(
                f"<iq type='set' from='focus@{DOMAIN}/focus' to='{full_jid}' "
                f"id='jibri-s-1'>"
                f"<jibri xmlns='http://jitsi.org/protocol/jibri' "
                f"action='start' room='{test_room}' session_id='{test_sid}'/>"
                f"</iq>",
                "jibri-start"
            )

            time.sleep(0.5)
            # Read responses: ACK + room presence
            for i in range(5):
                resp, buf = self._recv_stanza(conn, timeout=1)
                if resp:
                    log.info(f"<<< Response {i}: {resp[:200]}")

            # --- Colibri IQ ---
            log.info(">>> Colibri IQ")
            send(
                f"<iq type='set' from='jvb@{DOMAIN}/jvb' to='{full_jid}' "
                f"id='col-1'>"
                f"<jingle xmlns='urn:xmpp:jingle:1' action='session-initiate' "
                f"sid='{test_sid}'>"
                f"<content name='audio' creators='responder' senders='responder'>"
                f"<description xmlns='http://jitsi.org/protocol/colibri'/>"
                f"<transport xmlns='urn:xmpp:jingle:transports:ice-udp:1' "
                f"ufrag='tu' pwd='tp'>"
                f"<candidate component='1' foundation='1' "
                f"ip='10.0.0.5' port='50000' protocol='udp' "
                f"priority='2130706431' type='host'/>"
                f"</transport></content></jingle></iq>",
                "colibri"
            )

            time.sleep(0.5)
            for i in range(3):
                resp, buf = self._recv_stanza(conn, timeout=1)
                if resp:
                    log.info(f"<<< Response {i}: {resp[:200]}")

            # --- JibriIq STOP ---
            log.info(">>> JibriIq STOP")
            send(
                f"<iq type='set' from='focus@{DOMAIN}/focus' to='{full_jid}' "
                f"id='jibri-s-2'>"
                f"<jibri xmlns='http://jitsi.org/protocol/jibri' "
                f"action='stop' room='{test_room}' session_id='{test_sid}'/>"
                f"</iq>",
                "jibri-stop"
            )

            time.sleep(0.5)
            for i in range(5):
                resp, buf = self._recv_stanza(conn, timeout=1)
                if resp:
                    log.info(f"<<< Response {i}: {resp[:200]}")

            log.info("=" * 50)
            log.info("TEST SCENARIO COMPLETE")
            log.info("=" * 50)

        except Exception as e:
            log.error(f"Error: {e}", exc_info=True)
        finally:
            try:
                conn.close()
            except:
                pass
            log.info("Connection closed")

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(5)
        s.settimeout(1.0)
        log.info(f"Listening on {self.host}:{self.port}")
        while not self._stop.is_set():
            try:
                conn, addr = s.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(8)
                t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
        s.close()

    def stop(self):
        self._stop.set()


if __name__ == "__main__":
    s = MockXmppServer()
    try:
        s.start()
    except KeyboardInterrupt:
        s.stop()
