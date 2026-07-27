#!/bin/bash
# arvancloud-upload.sh — Upload a recording file to ArvanCloud VOD
set -euo pipefail

MP4_FILE="${1:-}"
ROOM="${2:-unknown}"
SESSION="${3:-001}"
STATE_DIR="/recordings/state"

[ -z "$MP4_FILE" ] && exit 0
[ ! -f "$MP4_FILE" ] && exit 0

MARKER="${STATE_DIR}/$(basename "$MP4_FILE").uploaded"
mkdir -p "${STATE_DIR}/players"
[ -f "$MARKER" ] && exit 0

CHANNEL_ID="${ARVAN_CHANNEL_ID:-}"
BASE="${ARVAN_VOD_BASE_URL:-https://napi.arvancloud.ir/vod/2.0}"

# Build auth header from env var (avoids the literal string in content)
# ARVAN_API_KEY should be "apikey <uuid>" — use as-is
AUTH_VAL="${ARVAN_API_KEY:-}"
if [ -z "$AUTH_VAL" ] || [ -z "$CHANNEL_ID" ]; then
  echo "[FAIL] ARVAN_API_KEY or ARVAN_CHANNEL_ID not set"
  exit 0
fi

TIMESTAMP=$(date -d "@$(stat -c %Y "$MP4_FILE")" '+%Y/%m/%d %H:%M:%S' 2>/dev/null || date '+%Y/%m/%d %H:%M:%S')
TITLE="$ROOM $TIMESTAMP"

FILESIZE=$(stat -c %s "$MP4_FILE")
FILENAME=$(basename "$MP4_FILE")
FILENAME_B64=$(echo -n "$FILENAME" | base64 -w0)
FILETYPE_B64=$(echo -n "video/mp4" | base64 -w0)

echo "[UPLOAD] $FILENAME -> $TITLE ($FILESIZE bytes)"

# STEP 1: Initiate tus upload
LOCATION=$(curl -s -D - \
  -X POST "${BASE}/channels/${CHANNEL_ID}/files" \
  -H "Authorization: ${AUTH_VAL}" \
  -H "tus-resumable: 1.0.0" \
  -H "upload-length: $FILESIZE" \
  -H "upload-metadata: filename $FILENAME_B64,filetype $FILETYPE_B64" \
  2>/dev/null | grep -i "^location:" | awk '{print $2}' | tr -d '\r\n')

if [ -z "$LOCATION" ]; then
  echo "[FAIL] $FILENAME - tus initiation failed"
  exit 0
fi

FILE_ID=$(echo "$LOCATION" | awk -F/ '{print $NF}')

# STEP 2: Upload bytes
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$LOCATION" \
  -H "Authorization: ${AUTH_VAL}" \
  -H "tus-resumable: 1.0.0" \
  -H "upload-offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary "@$MP4_FILE" \
  2>/dev/null)

if [ "$HTTP_CODE" != "204" ]; then
  echo "[FAIL] $FILENAME - tus upload failed (HTTP $HTTP_CODE)"
  exit 0
fi

# STEP 3: Create video entry
VIDEO_RESPONSE=$(curl -s \
  -X POST "${BASE}/channels/${CHANNEL_ID}/videos" \
  -H "Content-Type: application/json" \
  -H "Authorization: ${AUTH_VAL}" \
  -d "{\"title\":\"$TITLE\",\"file_id\":\"$FILE_ID\",\"convert_mode\":\"auto\"}" \
  2>/dev/null)

VIDEO_ID=$(echo "$VIDEO_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$VIDEO_ID" ]; then
  echo "[FAIL] $FILENAME - video creation failed"
  exit 0
fi

echo "[VIDEO] $FILENAME - created as $VIDEO_ID"

# STEP 4: Wait for processing
MAX_WAIT=300
WAIT_INTERVAL=10
ELAPSED=0
echo "[PROCESS] $FILENAME - waiting for conversion..."
while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(curl -s "${BASE}/videos/${VIDEO_ID}" \
    -H "Authorization: ${AUTH_VAL}" \
    -H "Accept: application/json" \
    2>/dev/null | jq -r '.data.status // "unknown"')
  case "$STATUS" in
    ready) echo "[PROCESS] $FILENAME - ready (${ELAPSED}s)"; break ;;
    converting_fail|error) echo "[FAIL] $FILENAME - conversion failed"; exit 0 ;;
    *) sleep "$WAIT_INTERVAL"; ELAPSED=$((ELAPSED + WAIT_INTERVAL)) ;;
  esac
done

# STEP 5: Player URL (secure link)
SECURE_KEY="${ARVAN_SECURE_LINK_KEY:-}"
if [ -n "$SECURE_KEY" ]; then
  SECURE_EXPIRE=$(($(date +%s) + 604800))
  VIDEO_DATA=$(curl -s \
    -X GET "${BASE}/videos/${VIDEO_ID}?secure_expire_time=$SECURE_EXPIRE" \
    -H "Authorization: ${AUTH_VAL}" \
    -H "Accept: application/json" \
    2>/dev/null)
  PLAYER_URL=$(echo "$VIDEO_DATA" | jq -r '.data.player_url // empty')
  if [ -n "$PLAYER_URL" ]; then
    echo "$PLAYER_URL" > "${STATE_DIR}/players/${ROOM}.url"
    echo "[SECURE] $FILENAME - player URL saved"
    echo "         $PLAYER_URL"
  fi
fi

date -u +%FT%TZ > "$MARKER"
echo "[DONE] $FILENAME - $TITLE"
