# LightRec v3 — Lightweight Jitsi Recording Orchestrator

A Python-based Jibri orchestration layer that replaces the static Jibri pool
with an intelligent dispatcher. LightRec connects to the brewery MUC, receives
recording triggers from Jicofo, and launches on-demand Jibri containers.

## Architecture v3 (current — Orchestrator Mode)

```
┌──────────────┐    XMPP (raw socket)    ┌──────────┐
│   LightRec   │◄───────────────────────►│  Prosody  │
│  (Python)    │   Join brewery MUC      │ (XMPP)   │
│              │   (jibri@auth.meet.jitsi)└────┬─────┘
│              │                               │
│              │   JibriIq (recording trigger)  │
│              │◄──────────────────────────────┤
│              │                               │
│              │   Launch Jibri containers     │
│              │─────────► docker run ...      │
│              │         (on-demand)           │
└──────────────┘
```

### How it works

1. **LightRec starts** → connects to Prosody C2S as `jibri@auth.meet.jitsi`
2. **Joins brewery** → `jibribrewery@internal-muc.meet.jitsi`
3. **Sends Jibri presence** → includes `<jibri-status>` and `<health-status>` as **sibling** elements (not nested — critical fix!)
4. **Jicofo detects LightRec** → lists it as an available Jibri instance
5. **User clicks Record** → Jicofo sends JibriIq to LightRec
6. **LightRec ACKs** → sends IQ result back immediately (avoids 15s timeout)
7. **LightRec delegates** → launches a Jibri Docker container for the room
8. **Jibri records** → Chrome + Selenium process inside the container

### Key Fix: Presence Format

Jicofo's `HealthStatusPacketExt` (Java Smack extension) expects `health-status`
as a **direct child of `<presence>`**, NOT nested inside `<jibri-status>`.

**✅ CORRECT (what LightRec v3 sends):**
```xml
<presence to='jibribrewery@internal-muc.meet.jitsi/lightrec-xxx'>
  <x xmlns='http://jabber.org/protocol/muc'/>
  <jibri-status xmlns='http://jitsi.org/protocol/jibri'>
    <busy-status>idle</busy-status>
  </jibri-status>
  <health-status xmlns='http://jitsi.org/protocol/health'>HEALTHY</health-status>
</presence>
```

**❌ WRONG (v2 had this — `available = false`):**
```xml
<jibri-status xmlns='http://jitsi.org/protocol/jibri'>
  <busy-status>idle</busy-status>
  <health-status>HEALTHY</health-status>  <!-- NESTED — WRONG -->
</jibri-status>
```

## Files

| File | Purpose |
|------|---------|
| `lightrec.py` | Main orchestrator — XMPP client + Docker orchestration |
| `Dockerfile` | Minimal image based on `jitsi/jibri:unstable` |
| `docker-compose.lightrec.yml` | Docker Compose service definition |
| `deploy-lightrec.sh` | Deployment script for the server |
| `test_lightrec_unit.py` | 26 unit tests (no network needed) |
| `test_presence_format.py` | Presence format verification |

## Testing locally

```bash
# Unit tests (no network/Docker needed):
cd custom-recorder
python3 test_lightrec_unit.py

# Presence format verification:
python3 test_presence_format.py

# Full XMPP test (requires SOCKS5 proxy to reach server):
python3 test_xmpp_full.py
```

## Deployment

```bash
# On the server (37.32.20.70):
cd ~/jitsi-infinity
bash custom-recorder/deploy-lightrec.sh

# Or step by step:
docker compose -f docker-compose.yml -f custom-recorder/docker-compose.lightrec.yml build lightrec
docker compose -f docker-compose.yml -f custom-recorder/docker-compose.lightrec.yml up -d lightrec
docker logs jitsi-lightrec -f
```

## Status

| Component | Status |
|-----------|--------|
| XMPP connection (raw socket) | ✅ Working |
| SASL PLAIN auth | ✅ Working |
| Brewery MUC join | ✅ Working |
| Presence format (sibling health-status) | ✅ Fixed in v3 |
| IQ response (ACK to Jicofo) | ✅ Implemented |
| Jibri container launch | ✅ Implemented |
| Reconnection logic | ✅ Implemented |
| Stop recording | ⚠️ Basic (docker stop + rm) |
| WebRTC direct capture | ❌ Blocked (av version mismatch) — orchestrator mode instead |
| Recording to file (direct) | ❌ Not needed — Jibri handles this |
| ArvanCloud upload | ❌ Separate service handles this |
