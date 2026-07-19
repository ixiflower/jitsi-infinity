#!/bin/bash
# watch-and-transcode.sh
# Watches /recordings/ for completed Jibri recordings and auto-transcodes to HLS.
# Designed to run inside the vod-transcoder Docker container.
#
# This runs alongside (not replacing) the ArvanCloud upload watcher.
# A recording can be both uploaded to CDN AND available locally as encrypted HLS.

set -euo pipefail

RECORDINGS_DIR="${RECORDINGS_DIR:-/recordings}"
VOD_DIR="${VOD_DIR:-/vod}"
STATE_DIR="${STATE_DIR:-/state/transcoded}"
TRANSCODE_SCRIPT="${TRANSCODE_SCRIPT:-/usr/local/bin/transcode-to-hls.sh}"
INTERVAL="${WATCH_INTERVAL:-30}"

mkdir -p "$STATE_DIR" "$VOD_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

process_recordings() {
    for dir in "$RECORDINGS_DIR"/*/; do
        [ -d "$dir" ] || continue
        uuid=$(basename "$dir")

        # Skip if already transcoded
        [ -f "$STATE_DIR/$uuid" ] && continue

        # Skip if recording is not complete yet (no mp4)
        ls "$dir"/*.mp4 &>/dev/null || continue

        log "New recording: $uuid"

        if bash "$TRANSCODE_SCRIPT" "$uuid"; then
            date -u +%FT%TZ > "$STATE_DIR/$uuid"
            log "Transcoded: $uuid"
        else
            log "FAILED transcoding: $uuid (will retry next cycle)"
        fi
    done

    # ── Cleanup: remove HLS for deleted source recordings ─────
    for vod_dir in "$VOD_DIR"/*/; do
        [ -d "$vod_dir" ] || continue
        vod_uuid=$(basename "$vod_dir")
        if [ ! -d "$RECORDINGS_DIR/$vod_uuid" ]; then
            log "Orphan VOD (source deleted): $vod_uuid — removing HLS"
            rm -rf "$vod_dir"
            rm -f "$STATE_DIR/$vod_uuid"
        fi
    done
}

log "VOD transcoder watching $RECORDINGS_DIR every ${INTERVAL}s..."
log "Output: $VOD_DIR"

while true; do
    process_recordings
    sleep "$INTERVAL"
done
