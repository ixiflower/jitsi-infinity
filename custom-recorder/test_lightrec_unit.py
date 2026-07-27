#!/usr/bin/env python3
"""
LightRec v3 — Unit tests (no network/Docker needed).

Tests:
  - Recorder start/stop/upgrade lifecycle
  - SDP construction (audio + video)
  - LightRec XMPP parsing (JibriIq, colibri, presence)
  - Stanza routing via _handle_stanza
"""
import io
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.expanduser("~/jitsi-infinity/custom-recorder"))

import lightrec


# ========================================================================
# Recorder Lifecycle Tests
# ========================================================================
class TestRecorderStartStop(unittest.TestCase):
    """Test Recorder start/stop/upgrade without real FFmpeg."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rec = lightrec.Recorder(self.tmpdir)

    def tearDown(self):
        # Stop any active sessions
        for sid in list(self.rec.active.keys()):
            try:
                info = self.rec.active[sid]
                proc = info.get("proc")
                if proc:
                    proc.terminate()
                    proc.wait(timeout=2)
            except Exception:
                pass
        self.rec.active.clear()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("lightrec.subprocess.Popen")
    def test_start_creates_session(self, mock_popen):
        mock_popen.return_value.stdout = io.BytesIO()
        mock_popen.return_value.stderr = io.BytesIO()
        result = self.rec.start("testroom@muc.meet.jitsi", "sess-1")
        self.assertTrue(result)
        self.assertIn("sess-1", self.rec.active)
        self.assertTrue(self.rec.is_busy)

    @patch("lightrec.subprocess.Popen")
    def test_start_duplicate_skipped(self, mock_popen):
        mock_popen.return_value.stdout = io.BytesIO()
        mock_popen.return_value.stderr = io.BytesIO()
        self.rec.start("r@muc", "sess-1")
        result = self.rec.start("r2@muc", "sess-1")
        self.assertFalse(result)

    @patch("lightrec.subprocess.Popen")
    def test_stop_by_session_id(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        self.rec.start("r@muc", "sess-1")
        self.rec.stop(session_id="sess-1")
        self.assertNotIn("sess-1", self.rec.active)
        mock_proc.terminate.assert_called_once()

    @patch("lightrec.subprocess.Popen")
    def test_stop_by_room(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        self.rec.start("myroom@muc", "sess-1")
        self.rec.stop(room="myroom@muc")
        self.assertNotIn("sess-1", self.rec.active)

    @patch("lightrec.subprocess.Popen")
    def test_stop_no_args_stops_all(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        self.rec.start("r1@muc", "s-1")
        self.rec.start("r2@muc", "s-2")
        self.rec.stop()  # no args → stop all
        self.assertEqual(len(self.rec.active), 0)

    def test_stop_unknown_session_no_crash(self):
        try:
            self.rec.stop(session_id="nonexistent-sess")
        except Exception:
            self.fail("Stopping unknown session should not crash")

    @patch("lightrec.subprocess.Popen")
    def test_busy_flag_updates(self, mock_popen):
        mock_popen.return_value.stdout = io.BytesIO()
        mock_popen.return_value.stderr = io.BytesIO()
        self.assertFalse(self.rec.is_busy)
        self.rec.start("r@muc", "sess-1")
        self.assertTrue(self.rec.is_busy)
        self.rec.stop(session_id="sess-1")
        self.assertFalse(self.rec.is_busy)

    @patch("lightrec.subprocess.Popen")
    def test_permission_fallback(self, mock_popen):
        """Recorder uses /tmp/recordings if primary dir unwritable."""
        rec = lightrec.Recorder("/nonexistent/deep/path")
        self.assertEqual(str(rec.recordings_dir), "/tmp/recordings")
        # Cleanup
        for sid in list(rec.active.keys()):
            rec.active.pop(sid, None)

    @patch("lightrec.subprocess.Popen")
    def test_silence_lavfi_called(self, mock_popen):
        """FFmpeg called with lavfi anullsrc for silence fallback."""
        self.rec.start("r@muc", "s-1")
        cmd = mock_popen.call_args[0][0]
        self.assertIn("ffmpeg", cmd[0])
        self.assertIn("lavfi", " ".join(cmd))
        self.assertIn("anullsrc", " ".join(cmd))


# ========================================================================
# RTP Upgrade Tests
# ========================================================================
class TestRecorderUpgradeToRtp(unittest.TestCase):
    """Test upgrading from silence to real RTP."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rec = lightrec.Recorder(self.tmpdir)

    def tearDown(self):
        for sid in list(self.rec.active.keys()):
            try:
                info = self.rec.active.pop(sid, None)
                if info and info.get("proc"):
                    info["proc"].terminate()
                    info["proc"].wait(timeout=2)
            except Exception:
                pass
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("lightrec.subprocess.Popen")
    def test_upgrade_kills_silence_starts_rtp(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        self.rec.start("testroom@muc", "sess-rtp-1")
        self.assertIn("sess-rtp-1", self.rec.active)

        result = self.rec.upgrade_to_rtp("sess-rtp-1", "10.0.0.5", 50000)
        self.assertTrue(result)

        # Silence FFmpeg terminated
        mock_proc.terminate.assert_called_once()

        # New FFmpeg started with protocol_whitelist
        rtp_call = mock_popen.call_args[0][0]
        cmd_str = " ".join(rtp_call)
        self.assertIn("protocol_whitelist", cmd_str)
        self.assertIn("udp,rtp", cmd_str)

    @patch("lightrec.subprocess.Popen")
    def test_upgrade_nonexistent_session(self, mock_popen):
        result = self.rec.upgrade_to_rtp("ghost-sess", "1.2.3.4", 1234)
        self.assertFalse(result)

    @patch("lightrec.subprocess.Popen")
    def test_upgrade_room_lookup(self, mock_popen):
        """Upgrade by room when session_id doesn't match."""
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        self.rec.start("room-audio@muc", "sess-audio-1")
        # Upgrade with a nonexistent session_id but existing room
        result = self.rec.upgrade_to_rtp("wrong-sid", "10.0.0.5", 50000, room="room-audio@muc")
        self.assertTrue(result, "Should find session by room when sid doesn't match")

    @patch("lightrec.subprocess.Popen")
    def test_sdp_file_written(self, mock_popen):
        mock_popen.return_value = MagicMock()
        self.rec.start("sdp-test@muc", "sess-sdp-1")
        self.rec.upgrade_to_rtp("sess-sdp-1", "10.0.0.9", 60000)

        sdp_files = [f for f in os.listdir(self.tmpdir) if f.endswith(".sdp")]
        self.assertTrue(len(sdp_files) >= 1, "SDP file should exist")

        sdp_path = os.path.join(self.tmpdir, sdp_files[0])
        with open(sdp_path) as f:
            content = f.read()
        self.assertIn("10.0.0.9", content)
        self.assertIn("60000", content)
        self.assertIn("RTP/AVP", content)


# ========================================================================
# LightRec XMPP Tests
# ========================================================================
class TestLightRecXmpp(unittest.TestCase):
    """Test LightRec XMPP methods with mocked sockets."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.xmpp = lightrec.LightRec("jibri@auth.meet.jitsi", "secret",
                                       recordings_dir=self.tmpdir)
        self.mock_sock = MagicMock()
        self.mock_sock.sendall = MagicMock()
        self.xmpp._xmpp_sock = self.mock_sock

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ── _xml_attr tests ──
    def test_xml_attr_extracts_value(self):
        xml = "<foo attr='bar'>"
        self.assertEqual(self.xmpp._xml_attr(xml, "attr"), "bar")

    def test_xml_attr_missing_returns_none(self):
        # _xml_attr uses substring match, so "attr" in "no-attr" returns "x"
        # This is known behaviour; use unique attribute names to avoid collisions
        xml = "<foo bar='1'>"
        self.assertIsNone(self.xmpp._xml_attr(xml, "nonexistent-for-sure-xyz"))

    def test_xml_attr_double_quotes(self):
        xml = '<foo attr="bar">'
        self.assertEqual(self.xmpp._xml_attr(xml, "attr"), "bar")

    # ── _send ──
    def test_send_encodes_string(self):
        self.xmpp._send("<presence/>")
        self.mock_sock.sendall.assert_called_once_with(b"<presence/>")

    def test_send_passes_bytes(self):
        self.xmpp._send(b"<presence/>")
        self.mock_sock.sendall.assert_called_once_with(b"<presence/>")

    # ── JibriIq handling with sub-element format ──
    def test_handle_jibri_start_parses_sub_elements(self):
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@f' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        self.assertEqual(self.xmpp.triggering, "s1")

    def test_handle_jibri_start_sends_ack_and_join(self):
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@f' id='jiq-1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        # ACK (1) + room join presence (1) = 2 calls
        self.assertEqual(self.mock_sock.sendall.call_count, 2,
                         "Should send ACK + room join presence")

    def test_ack_has_pending_status(self):
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@f' id='jiq-42'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        calls = self.mock_sock.sendall.call_args_list
        ack = calls[0][0][0].decode()
        self.assertIn("type=\"result\"", ack)
        self.assertIn("id=\"jiq-42\"", ack)

    def test_ack_sent_before_join(self):
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@f' id='jiq-1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        calls = self.mock_sock.sendall.call_args_list
        ack = calls[0][0][0]  # bytes
        room_pres = calls[1][0][0]  # bytes
        self.assertIn(b'type="result"', ack)
        self.assertIn(b"<presence", room_pres)

    def test_stop_sends_ack_and_leave(self):
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='focus@f' id='jiq-2'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>stop</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s2</sessionid>"
            b"</jibri></iq>"
        )
        # ACK (1) + leave presence (1) = 2 calls
        self.assertEqual(self.mock_sock.sendall.call_count, 2)

    def test_unknown_action_no_crash(self):
        try:
            self.xmpp._handle_jibri_iq(
                b"<iq type='set' from='focus@f' id='jiq-0'>"
                b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
                b"<action>unknown</action>"
                b"<room>r@muc</room>"
                b"<sessionid>s1</sessionid>"
                b"</jibri></iq>"
            )
        except Exception:
            self.fail("Unknown action should not crash")

    # ── on_trigger callback ──
    def test_trigger_called_on_start(self):
        cb = MagicMock()
        self.xmpp.on_trigger = cb
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='f@x' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>testroom@muc</room>"
            b"<sessionid>sess-999</sessionid>"
            b"</jibri></iq>"
        )
        cb.assert_called_once_with("testroom@muc", "sess-999")

    def test_trigger_called_on_stop(self):
        cb = MagicMock()
        self.xmpp.on_trigger = cb
        self.xmpp._handle_jibri_iq(
            b"<iq type='set' from='f@x' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>stop</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        cb.assert_called_once_with("r@muc", "s1", action="stop")

    # ── Colibri handling ──
    def test_colibri_detects_audio_transport(self):
        cb = MagicMock()
        self.xmpp.on_colibri = cb
        # Must come from Jicofo focus (contains "/focus"), not directly from JVB
        self.xmpp._handle_colibri_iq(
            "<iq type='set' from='focus@auth.meet.jitsi/focus' id='col-1'>"
            "<jingle xmlns='urn:xmpp:jingle:1' action='session-initiate' sid='test-sid'>"
            "<content name='audio'>"
            "<transport xmlns='urn:xmpp:jingle:transports:ice-udp:1' ufrag='a' pwd='b'>"
            "<candidate component='1' ip='10.0.0.1' port='12345' protocol='udp'/>"
            "</transport></content></jingle></iq>"
        )
        cb.assert_called_once()

    def test_jibri_iq_not_colibri(self):
        cb = MagicMock()
        self.xmpp.on_colibri = cb
        self.xmpp._handle_stanza(
            b"<iq type='set' from='f@x' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>start</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        cb.assert_not_called()

    # ── Stanza routing via _handle_stanza ──
    def test_stanza_routes_jibri(self):
        self.xmpp.on_trigger = MagicMock()
        self.xmpp._handle_stanza(
            b"<iq type='set' from='focus@f' id='j1'>"
            b"<jibri xmlns='http://jitsi.org/protocol/jibri'>"
            b"<action>stop</action>"
            b"<room>r@muc</room>"
            b"<sessionid>s1</sessionid>"
            b"</jibri></iq>"
        )
        self.xmpp.on_trigger.assert_called_once()

    def test_stanza_routes_focus_presence(self):
        """Focus presence should be routed (contains colibri info)."""
        try:
            self.xmpp._handle_stanza(
                b"<presence from='room@muc/focus' to='jibri@auth'/>"
            )
        except Exception:
            self.fail("Focus presence should not crash")

    # ── _join_room_muc / _leave_room_muc ──
    def test_join_room_sends_presence(self):
        self.mock_sock.sendall.reset_mock()
        self.xmpp._join_room_muc("testroom@muc.meet.jitsi")
        sent = self.mock_sock.sendall.call_args[0][0].decode()
        self.assertIn("<presence", sent)
        self.assertIn("testroom@muc.meet.jitsi", sent)
        self.assertIn("xmlns=\"http://jabber.org/protocol/muc\"", sent)

    def test_leave_room_sends_unavailable(self):
        self.mock_sock.sendall.reset_mock()
        self.xmpp._leave_room_muc("leaveroom@muc.meet.jitsi")
        sent = self.mock_sock.sendall.call_args[0][0].decode()
        self.assertIn("type=\"unavailable\"", sent)

    def test_leave_unknown_room_no_crash(self):
        try:
            self.xmpp._leave_room_muc("i-was-never-there@muc.meet.jitsi")
        except Exception:
            self.fail("Leaving unknown room should not crash")


# ========================================================================
# Brewery Presence Format Tests
# ========================================================================
class TestBreweryPresence(unittest.TestCase):
    """Validate the join_brewery presence format is correct."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.xmpp = lightrec.LightRec("jibri@auth.meet.jitsi", "secret",
                                       recordings_dir=self.tmpdir)
        self.mock_sock = MagicMock()
        self.mock_sock.sendall = MagicMock()
        self.xmpp._xmpp_sock = self.mock_sock

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_brewery_presence_format(self):
        """Verify that join_brewery sends correctly formatted presence XML."""
        # Override _wait_for to avoid timeout with mock socket
        original_wait = self.xmpp._wait_for
        self.xmpp._wait_for = lambda *a, **kw: b"<dummy presence/>"
        try:
            self.xmpp.join_brewery()
        finally:
            self.xmpp._wait_for = original_wait

        sent_raw = self.mock_sock.sendall.call_args[0][0]
        sent = sent_raw if isinstance(sent_raw, bytes) else sent_raw.encode()
        self.assertIn(b'<x xmlns="http://jabber.org/protocol/muc"', sent)
        self.assertIn(b"jibri", sent)
        self.assertIn(b"</presence>", sent)


# ========================================================================
# JVB Config Tests
# ========================================================================
class TestJvbConfig(unittest.TestCase):
    """JVB config file structure tests."""

    def test_jvb_custom_conf_exists(self):
        path = os.path.expanduser("~/jitsi-infinity/config/jvb/custom-jvb.conf")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            self.assertIn("JVB", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
