#!/usr/bin/env python3
"""Sync completed videos from ArvanCloud VOD API into local VOD player SQLite DB."""
import json, os, sqlite3, sys, urllib.request

# ── Config ──────────────────────────────────────────────────────────
def get_env(key, default=""):
    val = os.environ.get(key, "")
    if val:
        return val
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}=") and "=" in line:
                    return line.split("=", 1)[1].strip("\"'")
    return default

AUTH_VAL = get_env("ARVAN_API_KEY")
CHANNEL_ID = get_env("ARVAN_CHANNEL_ID", "3a0cd5ec-2a2a-4ad4-ac9b-bb39a90e6eec")
DB_PATH = get_env("VOD_DB", "/home/ubuntu/jitsi-infinity/vod-platform-app/vod.db")
BASE_URL = "https://napi.arvancloud.ir/vod/2.0"

if not AUTH_VAL:
    print("[SYNC] ARVAN_API_KEY not set", flush=True)
    sys.exit(1)

if AUTH_VAL.startswith("Authorization: "):
    AUTH_HEADER = AUTH_VAL
else:
    AUTH_HEADER = f"Authorization: {AUTH_VAL}"

# ── API caller ──────────────────────────────────────────────────────
def fetch_videos(page=1):
    url = f"{BASE_URL}/channels/{CHANNEL_ID}/videos?page={page}&per_page=50"
    req = urllib.request.Request(url)
    req.add_header("Authorization", AUTH_HEADER.split(": ", 1)[1])
    req.add_header("Accept", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[SYNC] API error: {e}", flush=True)
        return None

# ── Main ────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    c = conn.cursor()
    page = 1
    new_count, upd_count, skp_count, del_count = 0, 0, 0, 0

    # Collect all ArvanCloud video IDs that currently exist remotely
    remote_ids = set()

    while True:
        data = fetch_videos(page)
        if not data or "data" not in data:
            break
        items = data["data"]
        if not items:
            break

        for v in items:
            pid = v["id"]
            title = v["title"]
            player_url = v.get("player_url") or ""
            hls_url = v.get("hls_playlist") or ""
            thumbnail_url = v.get("thumbnail_url") or ""
            status = v.get("status")
            created_at = v.get("created_at", "")

            if not pid:
                continue
            remote_ids.add(pid)

            if not player_url or status != "complete":
                skp_count += 1
                continue

            # Look up by arvancloud_id
            existing = c.execute(
                "SELECT id, player_url, hls_url, thumbnail_url FROM videos WHERE arvancloud_id=?",
                (pid,)
            ).fetchone()

            if existing:
                vid, old_player_url, old_hls_url, old_thumb = existing
                # Update if changed
                if old_player_url != player_url or old_hls_url != hls_url or old_thumb != thumbnail_url:
                    c.execute(
                        "UPDATE videos SET player_url=?, hls_url=?, thumbnail_url=?, title=? WHERE id=?",
                        (player_url, hls_url, thumbnail_url, title, vid)
                    )
                    upd_count += 1
                    print(f"[SYNC] Updated: {title} ({pid})", flush=True)
                continue

            c.execute(
                "INSERT INTO videos (title, player_url, hls_url, thumbnail_url, arvancloud_id, visible, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (title, player_url, hls_url, thumbnail_url, pid, created_at),
            )
            print(f"[SYNC] Inserted: {title} ({pid})", flush=True)
            new_count += 1

        meta = data.get("meta", {})
        if page >= meta.get("last_page", 1):
            break
        page += 1

    # Delete entries whose arvancloud_id no longer exists on ArvanCloud
    if remote_ids:
        placeholders = ",".join("?" for _ in remote_ids)
        stale = c.execute(
            "SELECT id, title, arvancloud_id FROM videos WHERE arvancloud_id != '' AND arvancloud_id NOT IN ({})".format(placeholders),
            list(remote_ids)
        ).fetchall()
    else:
        stale = []

    for row in stale:
        vid, title, arid = row
        c.execute("DELETE FROM likes WHERE video_id=?", (vid,))
        c.execute("DELETE FROM comments WHERE video_id=?", (vid,))
        c.execute("DELETE FROM videos WHERE id=?", (vid,))
        print(f"[SYNC] Deleted stale: {title} (id={vid}, arvancloud={arid})", flush=True)
        del_count += 1

    conn.commit()
    conn.close()
    print(f"[SYNC] Done — {new_count} new, {upd_count} updated, {skp_count} skipped, {del_count} deleted", flush=True)

if __name__ == "__main__":
    main()
