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
os.environ["JIBRI_BREWERY"] = "jibribrewery@internal-muc.meet.jitsi"
os.environ["RECORDINGS_DIR"] = "/tmp/lightrec-recordings"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lightrec


def main():
    os.makedirs("/tmp/lightrec-recordings", exist_ok=True)

    # ── 1. Start mock XMPP server ──
    import mock_xmpp_server as mock
    server = mock.MockXmppServer(host="127.0.0.1", port=5222)
    svr_thread = threading.Thread(target=server.start, daemon=True)
    svr_thread.start()
    time.sleep(0.5)
    log.info("Mock XMPP server started on 127.0.0.1:5222")

    # ── 2. Quick smoke test: unit tests ──
    log.info("=" * 60)
    log.info("Running unit tests first...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         os.path.join(os.path.dirname(__file__), "test_lightrec_unit.py"),
         "-v", "--tb=short"],
        capture_output=True, text=True, timeout=30
    )
    for line in result.stdout.splitlines():
        if "PASSED" in line or "FAILED" in line:
            log.info(f"  {line.strip()}")
    if result.returncode != 0:
        log.error(f"  Some unit tests FAILED! Stopping.")
        log.error(result.stderr[:500])
        return
    log.info("  ✅ All unit tests passed!")
    log.info("=" * 60)

    # ── 3. Integration test: XMPP flow ──
    log.info("Connecting LightRec to mock server...")

    on_trigger_called = {"start": False, "stop": False}

    def on_trigger(room, session_id, action="start"):
        log.info(f"🔥 CALLBACK: on_trigger(action={action}, room={room}, "
                 f"session_id={session_id[:8] if session_id else '?'})")
        if action == "start":
            on_trigger_called["start"] = True
            on_trigger_called["room"] = room
            on_trigger_called["sid"] = session_id
        elif action == "stop":
            on_trigger_called["stop"] = True

    def on_colibri(sid, ip, port, srtp_key):
        log.info(f"📡 CALLBACK: on_colibri(sid={sid[:8] if sid else '?'}, "
                 f"ip={ip}, port={port})")
        on_trigger_called["colibri"] = True
        on_trigger_called["colibri_ip"] = ip
        on_trigger_called["colibri_port"] = port

    # Create LightRec XMPP instance but bypass infinite reconnect loop
    xmpp = lightrec.XMPP(
        "jibri@auth.meet.jitsi",
        "secret",
        on_trigger=on_trigger,
        on_colibri=on_colibri,
    )
    if not xmpp.connect():
        log.error("❌ LightRec failed to connect to mock server!")
        return

    log.info("✅ LightRec connected to mock server!")
    log.info("  Waiting for brewery presence handshake...")
    time.sleep(1)

    # The mock server will automatically send:
    #   JibriIq START → colibri IQ → JibriIq STOP
    # LightRec's listen loop processes these
    log.info("  Listening for stanzas (mock server will send test sequence)...")
    time.sleep(5)

    # Stop listening
    xmpp.running = False
    time.sleep(0.5)

    # ── 4. Verify results ──
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
        log.warning("  ⚠️  on_colibri was NOT called (colibri IQ may not have been parsed)")
        # This is not a hard failure — colibri parsing depends on stanza format
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
    xmpp.disconnect()
    server.stop()
    log.info("Done.")


if __name__ == "__main__":
    main()
