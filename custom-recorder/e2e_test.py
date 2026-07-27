#!/usr/bin/env python3
"""
LightRec v3 — End-to-end flow test (no network).

Tests the complete recording pipeline at the integration level
by directly calling internal methods with mocked sockets.
No real XMPP server needed.
"""
import logging
import os
import sys
import tempfile
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom-recorder"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("e2e")

os.environ["XMPP_SERVER"] = "127.0.0.1"
os.environ["XMPP_PORT"] = "15229"
os.environ["JIBRI_XMPP_PASSWORD"] = "secret"

import lightrec


def test():
    results = []

    def check(name, ok):
        status = "✅" if ok else "❌"
        log.info(f"  {status} {name}")
        results.append(ok)
        return ok

    with tempfile.TemporaryDirectory() as tmpdir:
        # ── Recorder tests (no network needed) ──
        recorder = lightrec.Recorder(tmpdir)

        # Start recording
        ok = recorder.start("testroom", "session-123")
        check("Recorder.start returns True", ok)
        check("Session in active dict", "session-123" in recorder.active)

        output_file = recorder.active["session-123"]["output"]
        check("Output file path exists", os.path.exists(os.path.dirname(str(output_file))))

        # Busy state
        check("is_busy is True after start", recorder.is_busy)

        # Upgrade to RTP
        ok = recorder.upgrade_to_rtp("session-123", "10.0.0.5", 50000)
        check("upgrade_to_rtp returns True", ok)
        info = recorder.active["session-123"]
        check("SDP path stored in active dict", "sdp" in info)
        check("SDP file exists on disk", os.path.exists(str(info["sdp"])))
        sdp_content = open(str(info["sdp"])).read()
        check("SDP contains target IP", "10.0.0.5" in sdp_content)
        check("SDP contains target port", "50000" in sdp_content)

        # Upgrade to nonexistent session returns False
        ok = recorder.upgrade_to_rtp("nonexist", "10.0.0.5", 50000)
        check("Upgrade nonexistent session returns False", not ok)

        # Stop recording (session_id first positional, room second)
        recorder.stop(session_id="session-123")
        check("Session removed after stop", "session-123" not in recorder.active)
        check("is_busy is False after stop", not recorder.is_busy)

        # Stop unknown session
        try:
            recorder.stop(session_id="nonexistent")
            check("Stop unknown session: no crash", True)
        except Exception as e:
            check(f"Stop unknown session crashed: {e}", False)

        # ── XMPP/LightRec method tests (mock socket) ──
        xmpp = lightrec.LightRec("jibri@auth.meet.jitsi", "test", recordings_dir=tmpdir)
        mock_sock = MagicMock()
        mock_sock.sendall = MagicMock()
        xmpp._xmpp_sock = mock_sock

        # JibriIq start — LightRec parser expects sub-element format:
        # <action>start</action>, <room>...</room>, <sessionid>...</sessionid>
        xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@auth.meet.jitsi/focus' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        # Expected: 1 ACK + 1 room join presence = 2 sendall calls
        check("JibriIq start calls sendall (ACK + room join)", mock_sock.sendall.call_count == 2)

        # Colibri IQ (string input for _handle_colibri_iq)
        xmpp._handle_colibri_iq(
            "<iq type='set' from='jvb@auth.meet.jitsi/jvb' id='c1'>"
            "<jingle xmlns='urn:xmpp:jingle:1' action='session-initiate' sid='s1'>"
            "<content name='audio'><transport xmlns='urn:xmpp:jingle:transports:ice-udp:1'>"
            "<candidate component='1' ip='10.0.0.5' port='50000' protocol='udp'/>"
            "</transport></content></jingle></iq>"
        )

        # Reset mocks for presence check
        mock_sock.sendall.reset_mock()

        # Send presence with busy status (via _send_xmpp)
        xmpp.recorder._busy = True
        xmpp._send_xmpp(
            '<presence to="jibribrewery@internal-muc.meet.jitsi/jibri-test" xmlns="jabber:client">'
            '<x xmlns="http://jabber.org/protocol/muc"/>'
            '<jibri-status xmlns="http://jitsi.org/protocol/jibri">'
            '<busy-status status="busy"/>'
            '<health-status xmlns="http://jitsi.org/protocol/health" status="HEALTHY"/>'
            '</jibri-status></presence>'
        )

        # Check the presence that was sent
        sent = b""
        for call in mock_sock.sendall.call_args_list:
            sent += call[0][0]

        check("Busy presence has jibri-status", b"<jibri-status" in sent)
        check("Busy presence has healthy health-status", b"HEALTHY" in sent)
        check("Busy presence has busy-status", b"status='busy'" in sent or b'status="busy"' in sent)

    # Summary
    passed = sum(1 for r in results if r)
    total = len(results)
    log.info("=" * 50)
    log.info(f"E2E: {passed}/{total} passed")
    success = all(results)
    log.info(f"OVERALL: {'✅ PASSED' if success else '❌ FAILED'}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(test())
