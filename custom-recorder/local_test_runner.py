#!/usr/bin/env python3
"""
LightRec Local Integration Test Runner.

Starts a mock XMPP server, connects LightRec to it, and runs through
the full recording lifecycle:
  JibriIq START → join conference MUC → colibri IQ → JibriIq STOP

Usage:
  source custom-recorder/.venv/bin/activate
  python3 custom-recorder/local_test_runner.py
"""
import logging
import os
import sys
import threading
import time

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [TEST] %(levelname)s %(message)s")
log = logging.getLogger("local-test")

# Set env vars for mock server BEFORE importing lightrec
os.environ["XMPP_SERVER"] = "127.0.0.1"
os.environ["XMPP_PORT"] = "5222"
os.environ["JIBRI_XMPP_PASSWORD"] = "secret"  # mock accepts any password
os.environ["RECORDINGS_DIR"] = "/tmp/lightrec-recordings"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lightrec
import mock_xmpp_server as mock


def main():
    os.makedirs("/tmp/lightrec-recordings", exist_ok=True)

    # ── 1. Start mock XMPP server ──
    mock_path = os.path.join(os.path.dirname(__file__), "mock_xmpp_server.py")
    server = mock.MockXmppServer(host="127.0.0.1", port=5222)
    svr_thread = threading.Thread(target=server.start, daemon=True)
    svr_thread.start()
    time.sleep(0.5)
    log.info("Mock XMPP server started on 127.0.0.1:5222")

    # ── 2. Connect LightRec ──
    log.info("=" * 60)
    log.info("Connecting LightRec to mock server...")

    on_trigger_called = {"start": False, "stop": False}
    trigger_lock = threading.Lock()

    def on_trigger(room, session_id, action="start"):
        with trigger_lock:
            log.info(f"🔥 CALLBACK: on_trigger(action={action}, room={room}, "
                     f"session_id={session_id[:8] if session_id else '?'})")
            on_trigger_called["action"] = action
            if action == "start":
                on_trigger_called["start"] = True
                on_trigger_called["room"] = room
                on_trigger_called["sid"] = session_id
            elif action == "stop":
                on_trigger_called["stop"] = True

    def on_colibri(sid, ip, port, room_jid, srtp_key=None, video_ip=None, video_port=None):
        with trigger_lock:
            log.info(f"📡 CALLBACK: on_colibri(sid={sid[:8] if sid else '?'}, "
                     f"ip={ip}, port={port})")
            on_trigger_called["colibri"] = True
            on_trigger_called["colibri_ip"] = ip
            on_trigger_called["colibri_port"] = port

    # Create and connect LightRec
    xmpp = lightrec.LightRec(
        "jibri@auth.meet.jitsi",
        "secret",
        recordings_dir="/tmp/lightrec-recordings",
    )
    xmpp.on_trigger = on_trigger
    xmpp.on_colibri = on_colibri

    if not xmpp.connect():
        log.error("❌ LightRec failed to connect to mock server!")
        return

    log.info("✅ LightRec TCP/TLS connected!")

    if not xmpp.authenticate():
        log.error("❌ LightRec SASL authentication failed!")
        return
    log.info("✅ LightRec authenticated!")

    if not xmpp.bind_resource():
        log.error("❌ LightRec resource binding failed!")
        return
    log.info("✅ LightRec bound!")

    if not xmpp.join_brewery():
        log.error("❌ LightRec brewery join failed!")
        return
    log.info("✅ LightRec joined brewery!")

    # ── 3. Start listener in background ──
    listener_thread = threading.Thread(target=xmpp.listen, daemon=True)
    listener_thread.start()
    time.sleep(0.5)
    log.info("✅ LightRec listener started")
    log.info("  Mock server will send: JibriIq START → colibri IQ → JibriIq STOP")
    log.info("  Waiting for triggers (8 seconds)...")

    # The mock server sends stanzas ~1s after brewery join
    time.sleep(8)

    # ── 4. Stop and verify ──
    xmpp.running = False
    time.sleep(0.3)

    log.info("=" * 60)
    log.info("VERIFICATION")
    log.info(f"  on_trigger(start) called: {on_trigger_called.get('start', False)}")
    log.info(f"  on_trigger(stop) called: {on_trigger_called.get('stop', False)}")
    log.info(f"  on_colibri called:       {on_trigger_called.get('colibri', False)}")

    passed = True
    if not on_trigger_called.get("start", False):
        log.error("  ❌ on_trigger(start) was NOT called")
        passed = False
    else:
        log.info(f"  ✅ JibriIq START received (room={on_trigger_called.get('room')})")

    if not on_trigger_called.get("colibri", False):
        log.warning("  ⚠️  on_colibri was NOT called (colibri IQ format mismatch?)")
    else:
        log.info(f"  ✅ Colibri IQ received "
                 f"({on_trigger_called.get('colibri_ip')}:"
                 f"{on_trigger_called.get('colibri_port')})")

    if not on_trigger_called.get("stop", False):
        log.error("  ❌ on_trigger(stop) was NOT called")
        passed = False
    else:
        log.info("  ✅ JibriIq STOP received")

    log.info("=" * 60)
    if passed:
        log.info("🎉 INTEGRATION TEST PASSED")
    else:
        log.warning("⚠️  Integration test had issues — check logs above")

    # Cleanup
    try:
        xmpp._xmpp_sock.close()
    except Exception:
        pass
    server.stop()
    log.info("Done.")


if __name__ == "__main__":
    main()
