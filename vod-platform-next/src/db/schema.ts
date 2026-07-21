import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

export const admins = sqliteTable("admins", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  username: text("username").notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  createdAt: text("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const videos = sqliteTable("videos", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  playerUrl: text("player_url").notNull(),
  hlsUrl: text("hls_url").default(""),
  arvancloudId: text("arvancloud_id").default(""),
  thumbnailUrl: text("thumbnail_url").default(""),
  visible: integer("visible").default(1),
  createdAt: text("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const likes = sqliteTable("likes", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  videoId: integer("video_id").notNull().references(() => videos.id),
  userToken: text("user_token").notNull(),
  createdAt: text("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const comments = sqliteTable("comments", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  videoId: integer("video_id").notNull().references(() => videos.id),
  userToken: text("user_token").notNull(),
  username: text("username").notNull(),
  text: text("text").notNull(),
  createdAt: text("created_at").default(sql`CURRENT_TIMESTAMP`),
});
