# LightRec — Lightweight Jitsi Recording Agent

A minimal, high-quality recorder for Jitsi Meet that replaces the heavy
Chrome+Selenium stack (Jibri) with a direct Python+WebRTC pipeline.

## Architecture

```
┌──────────────┐    XMPP (slixmpp)    ┌──────────┐
│   LightRec   │◄────────────────────►│  Prosody  │
│  (Python)    │    Join MUC room      │ (XMPP)   │
│              │                       └────┬─────┘
│              │                            │
│              │    Jingle (ICE/DTLS/SRTP)  │
│              │◄───────────────────────────┤
│              │                            │
│              │    RTP streams             │
│              │◄───────────────────────────┤
│              │                            │
│              │    Recording + Upload      │
│   recorder/  │──────► MP4 file ──► ArvanCloud
│   uploader/  │──────► VOD DB
└──────────────┘
```

## Components

### 1. XMPP Layer (`xmpp_client.py`)
- Connects to Prosody via C2S (port 5222)
- SASL PLAIN auth as `recorder@hidden.meet.jitsi`
- Joins MUC room (the conference)
- Registers Jingle IQ handler
- Receives session-init from Jicofo

### 2. WebRTC Layer (`webrtc_session.py`)
- Uses aiortc for RTP/RTCP handling
- ICE connectivity with JVB via Trickle ICE
- DTLS-SRTP key exchange  
- Receives audio (Opus) and video (VP8/VP9) streams
- Feeds raw packets to recorder

### 3. Recording Layer (`recorder.py`)
- Receives RTP packets from WebRTC session
- Demuxes audio/video into separate streams
- Uses ffmpeg (pipe) to mux into MP4
- Generates metadata (timestamps, participant info)

### 4. Upload Layer (`uploader.py`)
- After recording completes:
  1. Finalize MP4 file
  2. Upload to ArvanCloud via VOD API
  3. Insert record into VOD player SQLite DB
  4. Clean up local temp files

### 5. Dockerfile + entrypoint
- Minimal Alpine-based container
- Python 3.12 + required deps
- Runs as daemon, reads config from env vars

## Protocol Flow

1. LightRec starts → reads config (room JID, credentials, etc.)
2. Connects to Prosody C2S on 5222
3. Authenticates as recorder@hidden.meet.jitsi
4. Joins the MUC room as a participant
5. Jicofo sends Jingle `session-initiate` via the MUC
6. LightRec responds with `session-accept` (ICE candidates, DTLS fingerprint)
7. ICE connectivity with JVB establishes
8. DTLS handshake completes → SRTP keys derived
9. RTP streams flow in → captured → piped to ffmpeg
10. On stop signal → finalize MP4 → upload → cleanup

## Status

Phase 1 (XMPP): Planning
Phase 2 (WebRTC): Planning  
Phase 3 (Recording): Planning
Phase 4 (Integration): Planning

## References

- Jitsi protocol docs: https://jitsi.org/docs/
- aiortc: https://aiortc.readthedocs.io/
- slixmpp: https://slixmpp.readthedocs.io/
