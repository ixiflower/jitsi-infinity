import { NextRequest, NextResponse } from "next/server";
import { db } from "../../../../db";
import { videos, likes, comments } from "../../../../db/schema";
import { getAdminSession } from "../../../../lib/auth";
import { eq, sql } from "drizzle-orm";

// GET /api/videos/[id] — return a single video if visible (public)
export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  const video = db
    .select()
    .from(videos)
    .where(eq(videos.id, id))
    .get();

  if (!video || !video.visible) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  // Attach counts
  const likeCount = db
    .select({ count: sql<number>`count(*)` })
    .from(likes)
    .where(eq(likes.videoId, id))
    .get()?.count ?? 0;

  const commentCount = db
    .select({ count: sql<number>`count(*)` })
    .from(comments)
    .where(eq(comments.videoId, id))
    .get()?.count ?? 0;

  return NextResponse.json({ ...video, likeCount, commentCount });
}

// PATCH /api/videos/[id] — toggle visibility (admin only)
export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const isAdmin = await getAdminSession();
  if (!isAdmin) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  const video = db
    .select()
    .from(videos)
    .where(eq(videos.id, id))
    .get();

  if (!video) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const body = await req.json().catch(() => ({}));
  const updates: Record<string, any> = {};
  if (body.visible !== undefined) updates.visible = body.visible ? 1 : 0;
  else updates.visible = video.visible ? 0 : 1;
  if (body.title) updates.title = body.title;
  if (body.thumbnail_url !== undefined) updates.thumbnailUrl = body.thumbnail_url;

  const updated = db
    .update(videos)
    .set(updates)
    .where(eq(videos.id, id))
    .returning()
    .get();

  return NextResponse.json(updated);
}

// DELETE /api/videos/[id] — delete video + its likes/comments (admin only)
export async function DELETE(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const isAdmin = await getAdminSession();
  if (!isAdmin) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  // Delete related likes and comments first
  db.delete(likes).where(eq(likes.videoId, id)).run();
  db.delete(comments).where(eq(comments.videoId, id)).run();

  const deleted = db
    .delete(videos)
    .where(eq(videos.id, id))
    .returning()
    .get();

  if (!deleted) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  return NextResponse.json({ success: true, deleted });
}
