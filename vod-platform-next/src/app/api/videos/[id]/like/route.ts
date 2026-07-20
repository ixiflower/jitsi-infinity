import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { db } from "../../../../../db";
import { likes } from "../../../../../db/schema";
import { and, eq, sql } from "drizzle-orm";
import { randomUUID } from "crypto";

const USER_COOKIE = "user_token";

function getUserToken(): string {
  const store = cookies();
  let token = store.get(USER_COOKIE)?.value;
  if (!token) {
    token = randomUUID();
    store.set(USER_COOKIE, token, {
      httpOnly: true,
      secure: false,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 365, // 1 year
      path: "/",
    });
  }
  return token;
}

// POST /api/videos/[id]/like — toggle like
export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const videoId = parseInt(params.id, 10);
  if (isNaN(videoId)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  const userToken = getUserToken();

  // Check if like exists
  const existing = db
    .select()
    .from(likes)
    .where(and(eq(likes.videoId, videoId), eq(likes.userToken, userToken)))
    .get();

  if (existing) {
    // Unlike
    db.delete(likes)
      .where(and(eq(likes.videoId, videoId), eq(likes.userToken, userToken)))
      .run();
  } else {
    // Like
    db.insert(likes)
      .values({
        videoId,
        userToken,
        createdAt: new Date().toISOString(),
      })
      .run();
  }

  // Return updated count
  const count = db
    .select({ count: sql<number>`count(*)` })
    .from(likes)
    .where(eq(likes.videoId, videoId))
    .get()?.count ?? 0;

  return NextResponse.json({ liked: !existing, count });
}
