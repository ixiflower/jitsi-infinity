import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { createHash } from "crypto";
import path from "path";
import * as schema from "./schema";

const DB_PATH = process.env.SQLITE_PATH || path.join(process.cwd(), "vod.db");
const sqlite = new Database(DB_PATH);
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

// Auto-create tables
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    player_url TEXT NOT NULL,
    hls_url TEXT DEFAULT '',
    arvancloud_id TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    visible INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id),
    user_token TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video_id, user_token)
  );
  CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id),
    user_token TEXT NOT NULL,
    username TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
`);

// Seed default admin
const hash = createHash("sha256").update("admin").digest("hex");
sqlite.prepare("INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)").run("admin", hash);

// Seed test video if empty
const count = sqlite.prepare("SELECT COUNT(*) as c FROM videos").get() as { c: number };
if (count.c === 0) {
  sqlite.prepare(
    "INSERT INTO videos (title, player_url, hls_url) VALUES (?, ?, ?)"
  ).run(
    "🎬 Test Video — Secure Link Demo",
    "https://player.arvancloud.ir/index.html?config=https://jitsioffline.arvanvod.ir/emVlk5XqgA/b417104ef2c7a593a4a132865078da21/1785076959/jO2Dwx1JYV/origin_config.json?secure=true",
    "https://jitsioffline.arvanvod.ir/emVlk5XqgA/b417104ef2c7a593a4a132865078da21/1785076959/jO2Dwx1JYV/h_,144_200,240_400,360_546,480_546,720_546,k.mp4.list/master.m3u8?secure=true"
  );
}

export const db = drizzle(sqlite, { schema });
