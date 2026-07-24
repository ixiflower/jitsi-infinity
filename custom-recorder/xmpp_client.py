#!/usr/bin/env python3
"""
LightRec — Lightweight Jitsi Recording Agent
Phase 1: XMPP Connection to Prosody

Connects to Prosody, authenticates, joins a MUC room, and listens for
Jingle session-initiate from Jicofo (the recording trigger).
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

import slixmpp
from slixmpp.exceptions import IqError, IqTimeout

logger = logging.getLogger("lightrec.xmpp")

# ── Helpers ───────────────────────────────────────────────────────────
def load_env(path=".env"):
    env = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return env


# ── XMPP Client ───────────────────────────────────────────────────────
class LightRecXMPP(slixmpp.ClientXMPP):
    """Connects to Prosody, authenticates, joins a MUC, listens for IQs."""

    def __init__(self, jid, password, room, nick="lightrec"):
        super().__init__(jid, password)
        self.room = room
        self.nick = nick
        self.room_jid = f"{room}@muc.meet.jitsi"
        self.session_id = str(uuid.uuid4())

        # Plugins
        self.register_plugin("xep_0030")  # Service Discovery
        self.register_plugin("xep_0045")  # MUC
        self.register_plugin("xep_0085")  # Chat State Notifications
        self.register_plugin("xep_0199")  # XMPP Ping

        # Event handlers
        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("message", self.on_message)
        self.add_event_handler("groupchat_presence", self.on_muc_presence)
        self.add_event_handler("groupchat_message", self.on_muc_message)
        self.add_event_handler("disconnected", self.on_disconnect)

        # IQ handlers
        self.register_handler(
            slixmpp.IQHandler(
                iq=self._handle_jingle_iq,
                match=slixmpp.MatchXPath(
                    "{urn:xmpp:jingle:1}jingle"
                ),
            )
        )

        self.connected = asyncio.Event()
        self.joined_muc = asyncio.Event()

    async def on_session_start(self, event):
        """Connected to XMPP — join the MUC room."""
        logger.info(f"Connected as {self.boundjid}")
        self.send_presence()
        await self.get_roster()

        logger.info(f"Joining MUC: {self.room_jid}/{self.nick}")
        self.plugin["xep_0045"].join_muc(
            self.room_jid,
            self.nick,
            wait=True
        )
        self.connected.set()

    def on_message(self, msg):
        """Direct message handler."""
        if msg["type"] in ("chat", "normal"):
            logger.debug(f"DM from {msg['from']}: {msg['body']}")

    def on_muc_presence(self, pres):
        """MUC presence updates — log join/leave."""
        nick = pres["muc_nick"]
        if pres["type"] == "unavailable":
            logger.info(f"Participant left: {nick}")
        else:
            logger.info(f"Participant joined: {nick}")
            self.joined_muc.set()

    def on_muc_message(self, msg):
        """MUC room messages (for info, not media)."""
        body = msg.get("body", "")
        if body:
            logger.debug(f"[MUC] {msg['muc_nick']}: {body}")

    def on_disconnect(self, event):
        """Connection lost — log and exit."""
        logger.warning("Disconnected from XMPP")
        self.connected.clear()

    async def _handle_jingle_iq(self, iq):
        """Handle Jingle IQ from Jicofo (session-initiate)."""
        if iq["type"] == "set":
            jingle = iq["jingle"]
            action = jingle["action"]
            sid = jingle["sid"]
            logger.info(f"Jingle {action} sid={sid} from {iq['from']}")

            if action == "session-initiate":
                # We received a recording offer — this is the trigger!
                await self._handle_session_initiate(iq, jingle)
            elif action == "session-terminate":
                logger.info("Session terminated — recording done")
            elif action == "transport-info":
                logger.info("ICE candidate received")
            return self.make_iq_result(iq)

        return self.make_iq_error(iq)

    async def _handle_session_initiate(self, iq, jingle):
        """
        Handle Jingle session-initiate from Jicofo.
        This is where we'd set up the WebRTC connection.
        """
        logger.info("=" * 50)
        logger.info("RECORDING TRIGGERED! Session init received.")
        logger.info(f"  From: {iq['from']}")
        logger.info(f"  Room: {self.room}")
        logger.info(f"  SID:  {jingle['sid']}")
        logger.info("=" * 50)

        # TODO Phase 2: Set up aiortc WebRTC session
        # For now, just acknowledge

    async def start_recording_session(self):
        """
        Manually trigger recording by sending a start request to Jicofo
        (simulates what the Jitsi Meet client does when user clicks Record).
        """
        logger.info("Requesting recording start from Jicofo...")
        
        # Send JibriIq to Jicofo via the room's focus
        focus_jid = f"{self.room_jid}/focus"
        
        iq = self.Iq()
        iq["type"] = "set"
        iq["to"] = focus_jid
        iq["from"] = self.boundjid
        
        jibri = slixmpp.Element("jibri", {
            "xmlns": "http://jitsi.org/protocol/jibri",
            "action": "start",
            "recording_mode": "file",
            "room": self.room_jid,
            "session_id": self.session_id,
        })
        iq.append(jibri)
        
        try:
            result = await iq.send(timeout=10)
            logger.info(f"Recording start response: {result}")
            return True
        except IqError as e:
            logger.error(f"Recording start error: {e}")
        except IqTimeout:
            logger.error("Recording start timeout")
        return False


# ── Main ──────────────────────────────────────────────────────────────
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("slixmpp").setLevel(logging.WARNING)

    # Load credentials from .env.jibri
    env_path = Path(__file__).parent.parent / ".env.jibri"
    env = load_env(env_path)

    jid = env.get("XMPP_RECORDER_USER", "recorder@hidden.meet.jitsi")
    password = env.get("JIBRI_RECORDER_PASSWORD", "")
    room = os.environ.get("LIGHTREC_ROOM", "lightrec-test")

    if not password:
        logger.error("JIBRI_RECORDER_PASSWORD not found in .env.jibri")
        return

    xmpp = LightRecXMPP(jid, password, room)

    # Connect to Prosody
    xmpp.connect(("xmpp.meet.jitsi", 5222))
    
    # Wait for connection and MUC join
    await xmpp.connected.wait()
    await xmpp.joined_muc.wait()
    
    logger.info(f"Joined room {room}. Waiting for recording trigger...")
    
    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        xmpp.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
