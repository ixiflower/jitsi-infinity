#!/bin/bash
# transcode-to-hls.sh <session-uuid>
# Converts a Jibri .mp4 recording into AES-128 encrypted HLS (HTTP Live Streaming).
#
# Output per recording:
#   ./vod/<uuid>/
#     index.m3u8          — master playlist (references segments + key URI)
#     segment_000.ts       — 6-second encrypted video chunks
#     segment_001.ts
#     ...
#     key.key             — raw AES-128 key (16 hex bytes) — KEEP SECURE
#     key_info.txt         — ffmpeg key info file (key URI + path + key)
#
# The key URI embedded in the .m3u8 points to /vod-key/<uuid>
# which is served by Nginx with referrer-based access control.
# Without the key, .ts chunks are encrypted garbage.

set -euo pipefail

UUID="${1:-}"
RECORDINGS_DIR="${RECORDINGS_DIR:-/recordings}"
VOD_DIR="${VOD_DIR:-/vod}"
RESOLUTION="${VOD_RESOLUTION:-1280x720}"
CRF="${VOD_CRF:-23}"
SEGMENT_TIME="${VOD_SEGMENT_TIME:-6}"

usage() {
    echo "Usage: $0 <session-uuid>"
    echo ""
    echo "Converts a Jibri recording to AES-128 encrypted HLS."
    echo "Reads from \$RECORDINGS_DIR/<uuid>/*.mp4"
    echo "Writes to   \$VOD_DIR/<uuid>/"
    echo ""
    echo "Env vars:"
    echo "  VOD_RESOLUTION   Output resolution (default: 1280x720)"
    echo "  VOD_CRF          H.264 quality, lower=better (default: 23)"
    echo "  VOD_SEGMENT_TIME HLS segment duration in seconds (default: 6)"
    exit 1
}

[ -z "$UUID" ] && usage

SESSION_DIR="$RECORDINGS_DIR/$UUID"
OUT_DIR="$VOD_DIR/$UUID"

# ── Find the mp4 ──────────────────────────────────────────────
shopt -s nullglob
MP4_FILES=("$SESSION_DIR"/*.mp4)
shopt -u nullglob
MP4_FILE="${MP4_FILES[0]:-}"

if [ -z "$MP4_FILE" ]; then
    echo "[SKIP] $UUID — no .mp4 found in $SESSION_DIR"
    exit 1
fi

# ── Skip if already transcoded ────────────────────────────────
if [ -f "$OUT_DIR/index.m3u8" ]; then
    echo "[SKIP] $UUID — already transcoded ($OUT_DIR/index.m3u8 exists)"
    exit 0
fi

mkdir -p "$OUT_DIR"

# ── Generate AES-128 key (16 bytes = 32 hex chars) ────────────
KEY_FILE="$OUT_DIR/key.key"
openssl rand -hex 16 > "$KEY_FILE"
KEY_URI="${VOD_KEY_URI:-/vod-key/$UUID}"

# ── Key info file for ffmpeg ──────────────────────────────────
# Format: KEY_URI\nKEY_PATH\nKEY_VALUE\n[IV]\n
# KEY_URI  = what goes into the .m3u8 (#EXT-X-KEY:METHOD=AES-128,URI="...")
# KEY_PATH = local path for ffmpeg to read the key
# KEY_VALUE = the key itself (ffmpeg reads it from KEY_PATH if present)
KEY_INFO="$OUT_DIR/key_info.txt"
printf '%s\n' "$KEY_URI"  > "$KEY_INFO"
printf '%s\n' "$KEY_FILE" >> "$KEY_INFO"
cat "$KEY_FILE"           >> "$KEY_INFO"

echo "[TRANSCODE] $UUID — source: $(basename "$MP4_FILE") ($(du -h "$MP4_FILE" | cut -f1))"

# ── Transcode to HLS with AES-128 encryption ──────────────────
ffmpeg -y -hide_banner -loglevel warning -stats \
    -i "$MP4_FILE" \
    -vf "scale=${RESOLUTION}:force_original_aspect_ratio=decrease,pad=${RESOLUTION}:(ow-iw)/2:(oh-ih)/2" \
    -c:v libx264 -preset fast -crf "$CRF" -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ar 44100 \
    -hls_time "$SEGMENT_TIME" \
    -hls_list_size 0 \
    -hls_segment_type mpegts \
    -hls_segment_filename "$OUT_DIR/segment_%03d.ts" \
    -hls_key_info_file "$KEY_INFO" \
    -hls_flags independent_segments \
    -f hls "$OUT_DIR/index.m3u8"

# ── Verify ────────────────────────────────────────────────────
SEGMENT_COUNT=$(find "$OUT_DIR" -name 'segment_*.ts' | wc -l)
OUT_SIZE=$(du -sh "$OUT_DIR" | cut -f1)

echo "[DONE] $UUID → $SEGMENT_COUNT segments, $OUT_SIZE total"
echo "       Master: $OUT_DIR/index.m3u8"
echo "       Key:    $OUT_DIR/key.key"
