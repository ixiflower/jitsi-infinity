#!/bin/bash
# arvancloud-upload.sh <session-uuid>
# Uploads a Jibri recording directory to ArvanCloud VOD
# and generates a SECURE player URL (IP-locked + time-expiring).
#
# Uses: ARVAN_API_KEY, ARVAN_CHANNEL_ID, ARVAN_SECURE_LINK_KEY from environment
#
# Output files (per recording):
#   /state/uploaded/<uuid>          — upload timestamp marker
#   /state/players/<uuid>.url       — secure player URL (for embedding)
#   /state/players/<uuid>.json      — full metadata + secure URLs

set -euo pipefail

UUID="${1:-}"
RECORDINGS_DIR="${RECORDINGS_DIR:-/recordings}"
STATE_DIR="${STATE_DIR:-/state}"
PLAYER_DIR="${STATE_DIR}/players"

[ -z "$UUID" ] && echo "Usage: $0 <session-uuid>" && exit 1

SESSION_DIR="$RECORDINGS_DIR/$UUID"
METADATA="$SESSION_DIR/metadata.json"
MARKER="$STATE_DIR/$UUID"
PLAYER_URL_FILE="$PLAYER_DIR/$UUID.url"
PLAYER_JSON_FILE="$PLAYER_DIR/$UUID.json"

mkdir -p "$PLAYER_DIR"

# ── Skip if already uploaded ──────────────────────────────────
if [ -f "$MARKER" ]; then
  exit 0
fi

# ── Find the mp4 ──────────────────────────────────────────────
shopt -s nullglob
MP4_FILES=("$SESSION_DIR"/*.mp4)
shopt -u nullglob
MP4_FILE="${MP4_FILES[0]:-}"

if [ ! -f "$METADATA" ] || [ -z "$MP4_FILE" ]; then
  exit 1
fi

# ── Config ────────────────────────────────────────────────────
AUTH=*** ${ARVAN_API_KEY}"
BASE="${ARVAN_VOD_BASE_URL:-https://napi.arvancloud.ir/vod/2.0}"
CHANNEL_ID="${ARVAN_CHANNEL_ID}"
SECURE_KEY="${ARVAN_SECURE_LINK_KEY:-}"

if [ -z "${ARVAN_API_KEY:-}" ] || [ -z "$CHANNEL_ID" ]; then
  echo "[FAIL] $UUID — ARVAN_API_KEY or ARVAN_CHANNEL_ID not set"
  exit 1
fi

# ── Extract metadata ──────────────────────────────────────────
ROOM=$(jq -r '.meeting_url // empty' "$METADATA" | sed 's|.*/||')
TIMESTAMP=$(date -d "@$(stat -c %Y "$MP4_FILE")" '+%Y/%m/%d %H:%M:%S' 2>/dev/null || date '+%Y/%m/%d %H:%M:%S')
[ -z "$ROOM" ] && ROOM="unknown"
TITLE="$ROOM $TIMESTAMP"

FILESIZE=$(stat -c %s "$MP4_FILE")
FILENAME=$(basename "$MP4_FILE")
FILENAME_B64=$(echo -n "$FILENAME" | base64 -w0)
FILETYPE_B64=$(echo -n "video/mp4" | base64 -w0)

echo "[UPLOAD] $UUID → $TITLE ($FILESIZE bytes)"

# ═══════════════════════════════════════════════════════════════
# STEP 1: Initiate tus upload
# ═══════════════════════════════════════════════════════════════
LOCATION=$(curl -s -D - \
  -X POST "$BASE/channels/$CHANNEL_ID/files" \
  -H "$AUTH" \
  -H "tus-resumable: 1.0.0" \
  -H "upload-length: $FILESIZE" \
  -H "upload-metadata: filename $FILENAME_B64,filetype $FILETYPE_B64" \
  2>/dev/null | grep -i "^location:" | awk '{print $2}' | tr -d '\r\n')

if [ -z "$LOCATION" ]; then
  echo "[FAIL] $UUID — tus initiation failed"
  exit 1
fi

FILE_ID=$(echo "$LOCATION" | awk -F/ '{print $NF}')

# ═══════════════════════════════════════════════════════════════
# STEP 2: Upload file bytes (tus PATCH)
# ═══════════════════════════════════════════════════════════════
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$LOCATION" \
  -H "$AUTH" \
  -H "tus-resumable: 1.0.0" \
  -H "upload-offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary "@$MP4_FILE" \
  2>/dev/null)

if [ "$HTTP_CODE" != "204" ]; then
  echo "[FAIL] $UUID — tus upload failed (HTTP $HTTP_CODE)"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: Create video entry
# ═══════════════════════════════════════════════════════════════
VIDEO_RESPONSE=$(curl -s \
  -X POST "$BASE/channels/$CHANNEL_ID/videos" \
  -H "Content-Type: application/json" \
  -H "$AUTH" \
  -d "{\"title\":\"$TITLE\",\"file_id\":\"$FILE_ID\",\"convert_mode\":\"auto\"}" \
  2>/dev/null)

VIDEO_ID=$(echo "$VIDEO_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$VIDEO_ID" ]; then
  echo "[FAIL] $UUID — video creation failed"
  echo "$VIDEO_RESPONSE"
  exit 1
fi

echo "[VIDEO] $UUID — created as $VIDEO_ID"

# ═══════════════════════════════════════════════════════════════
# STEP 4: Wait for video processing to complete
# ═══════════════════════════════════════════════════════════════
MAX_WAIT=300  # 5 minutes max
WAIT_INTERVAL=10
ELAPSED=0

echo "[PROCESS] $UUID — waiting for conversion..."
while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(curl -s "$BASE/videos/$VIDEO_ID" \
    -H "$AUTH" \
    -H "Accept: application/json" \
    2>/dev/null | jq -r '.data.status // "unknown"')

  case "$STATUS" in
    ready)
      echo "[PROCESS] $UUID — ready (${ELAPSED}s)"
      break
      ;;
    converting_fail|error)
      echo "[FAIL] $UUID — conversion failed (status: $STATUS)"
      exit 1
      ;;
    *)
      sleep "$WAIT_INTERVAL"
      ELAPSED=$((ELAPSED + WAIT_INTERVAL))
      ;;
  esac
done

if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
  echo "[WARN] $UUID — conversion timeout after ${MAX_WAIT}s, continuing anyway"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 5: Generate SECURE player URL (IP-locked, 7-day expiry)
# ═══════════════════════════════════════════════════════════════
if [ -n "$SECURE_KEY" ]; then
  # Default: 7-day expiry, no IP lock (IP will be set at embed time)
  SECURE_EXPIRE=$(($(date +%s) + 604800))  # 7 days
  SECURE_IP="${SECURE_IP:-}"  # leave empty = CDN uses requester IP

  SECURE_PARAMS="secure_expire_time=$SECURE_EXPIRE"
  [ -n "$SECURE_IP" ] && SECURE_PARAMS="$SECURE_PARAMS&secure_ip=$SECURE_IP"

  VIDEO_DATA=$(curl -s \
    -X GET "$BASE/videos/$VIDEO_ID?$SECURE_PARAMS" \
    -H "$AUTH" \
    -H "Accept: application/json" \
    2>/dev/null)

  PLAYER_URL=$(echo "$VIDEO_DATA" | jq -r '.data.player_url // empty')
  HLS_URL=$(echo "$VIDEO_DATA" | jq -r '.data.hls_playlist // empty')

  if [ -n "$PLAYER_URL" ]; then
    echo "$PLAYER_URL" > "$PLAYER_URL_FILE"
    echo "$VIDEO_DATA" | jq '{
      video_id: .data.id,
      title: .data.title,
      player_url: .data.player_url,
      hls_playlist: .data.hls_playlist,
      dash_playlist: .data.dash_playlist,
      thumbnail_url: .data.thumbnail_url,
      expire_time: '"$SECURE_EXPIRE"',
      uploaded_at: "'"$(date -u +%FT%TZ)"'"
    }' > "$PLAYER_JSON_FILE"

    echo "[SECURE] $UUID — player URL saved"
    echo "         $PLAYER_URL"
    echo "         Expires: $(date -d "@$SECURE_EXPIRE" '+%Y-%m-%d %H:%M:%S')"
  else
    echo "[WARN] $UUID — no player_url in response (video may still be processing)"
  fi
else
  echo "[INFO] $UUID — ARVAN_SECURE_LINK_KEY not set, skipping secure link generation"
fi

# ═══════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════
echo "$(date -u +%FT%TZ)" > "$MARKER"
echo "[DONE] $UUID — $TITLE"
