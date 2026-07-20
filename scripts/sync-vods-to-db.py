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

# Normalize: if it already has "Authorization:" prefix, just use it directly
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
    page, inserted, skipped = 1, 0, 0

    while True:
        data = fetch_videos(page)
        if not data or "data" not in data:
            break
        videos = data["data"]
        if not videos:
            break

        for v in videos:
            pid = v["id"]
            title = v["title"]
            player_url = v.get("player_url")
            hls_url = v.get("hls_playlist") or ""
            status = v.get("status")
            created_at = v.get("created_at", "")

            if not player_url or status != "complete":
                skipped += 1
                continue

            c.execute("SELECT id FROM videos WHERE player_url=?", (player_url,))
            if c.fetchone():
                continue

            c.execute(
                "INSERT INTO videos (title, player_url, hls_url, visible, created_at) VALUES (?, ?, ?, 1, ?)",
                (title, player_url, hls_url, created_at),
            )
            print(f"[SYNC] Inserted: {title} ({pid})", flush=True)
            inserted += 1

        meta = data.get("meta", {})
        if page >= meta.get("last_page", 1):
            break
        page += 1

    conn.commit()
    conn.close()
    print(f"[SYNC] Done — {inserted} new, {skipped} incomplete/skipped", flush=True)

if __name__ == "__main__":
    main()
