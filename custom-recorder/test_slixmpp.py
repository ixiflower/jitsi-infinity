#!/usr/bin/env python3
"""LightRec Phase 1 — slixmpp test with direct address."""
import asyncio, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lightrec")
logging.getLogger("slixmpp").setLevel(logging.WARNING)

import slixmpp

class LightRec(slixmpp.ClientXMPP):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.register_plugin("xep_0030")
        self.register_plugin("xep_0045")
        self.register_plugin("xep_0199")
        self.add_event_handler("session_start", self.on_start)
        self.add_event_handler("disconnected", self.on_disc)
        self.add_event_handler("connection_failed", self.on_conn_fail)
        self.ready = asyncio.Event()

    async def on_conn_fail(self, event):
        log.error(f"Connection failed: {event}")

    async def on_start(self, event):
        log.info(f"Connected as {self.boundjid}")
        self.send_presence()
        await self.get_roster()
        brewery = "jibribrewery@internal-muc.meet.jitsi"
        log.info(f"Joining brewery: {brewery}")
        self.plugin["xep_0045"].join_muc(brewery, "lightrec")
        self.ready.set()
        log.info("Phase 1: PASS")

    def on_disc(self, event):
        log.warning("Disconnected")

async def main():
    env_path = Path("/app/.env.jibri")
    password = ""
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "JIBRI_RECORDER_PASSWORD" in line and "=" in line:
                password = line.split("=", 1)[1].strip().strip("\"'").strip()
    
    if not password:
        log.error("Password not found"); return

    xmpp = LightRec("recorder@hidden.meet.jitsi", password)
    xmpp.connect(("xmpp.meet.jitsi", 5222))
    await xmpp.ready.wait()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    xmpp.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
