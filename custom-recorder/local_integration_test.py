#!/usr/bin/env python3
"""
LightRec full integration test.
Starts mock server in a thread, runs LightRec connect, exercises JibriIq flow.
"""
import logging, os, sys, threading, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom-recorder"))
os.environ["XMPP_SERVER"] = "127.0.0.1"
os.environ["XMPP_PORT"] = "15225"
os.environ["JIBRI_XMPP_PASSWORD"] = "secret"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("test")

def run_test():
    # Start mock server on port 15225
    from mock_xmpp_server import MockXmppServer
    server = MockXmppServer(port=15225)
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    time.sleep(0.5)

    log.info("Starting LightRec...")
    import lightrec
    recorder = lightrec.Recorder("/tmp/lightrec-test")

    results = {"start": False, "colibri": False, "stop": False}

    def on_trigger(room, session_id, action="start"):
        log.info(f"🔥 on_trigger({action}, room={room})")
        if action == "start":
            recorder.start(room, session_id)
            results["start"] = True
        elif action == "stop":
            recorder.stop(room, session_id)
            results["stop"] = True

    def on_colibri(sid, ip, port, srtp_key):
        log.info(f"📡 on_colibri({sid[:8]}..., {ip}:{port})")
        recorder.upgrade_to_rtp(sid, ip, port, srtp_key)
        results["colibri"] = True

    xmpp = lightrec.XMPP("jibri@auth.meet.jitsi", "secret", on_trigger, on_colibri)
    ok = xmpp.connect()
    log.info(f"connect() = {ok}")
    if not ok:
        log.error("FAIL: connect() returned False")
        server.stop()
        return

    log.info("Starting listen thread (mock server will send test sequence)...")
    xmpp.running = True
    listen_thread = threading.Thread(target=xmpp.listen, daemon=True)
    listen_thread.start()

    # Wait for mock server to finish its scenario
    time.sleep(8)
    xmpp.running = False
    listen_thread.join(timeout=2)

    log.info("=" * 50)
    log.info("RESULTS")
    for k, v in results.items():
        log.info(f"  {k}: {'✅' if v else '❌'}")
    all_ok = all(results.values())
    log.info(f"OVERALL: {'✅ PASSED' if all_ok else '❌ FAILED'}")

    xmpp.disconnect()
    server.stop()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run_test()
