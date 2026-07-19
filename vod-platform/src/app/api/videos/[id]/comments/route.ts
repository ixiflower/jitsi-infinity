import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { db } from "../../../../../db";
import { comments } from "../../../../../db/schema";
import { desc, eq } from "drizzle-orm";
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
      maxAge: 60 * 60 * 24 * 365,
      path: "/",
    });
  }
  return token;
}

// GET /api/videos/[id]/comments — list comments for a video
export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const videoId = parseInt(params.id, 10);
  if (isNaN(videoId)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  const list = db
    .select()
    .from(comments)
    .where(eq(comments.videoId, videoId))
    .orderBy(desc(comments.createdAt))
    .all();

  return NextResponse.json(list);
}

// POST /api/videos/[id]/comments — add a comment
export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const videoId = parseInt(params.id, 10);
  if (isNaN(videoId)) {
    return NextResponse.json({ error: "Invalid video ID" }, { status: 400 });
  }

  let body: { username?: string; text?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { username, text } = body;
  if (!username || !text) {
    return NextResponse.json(
      { error: "username and text are required" },
      { status: 400 }
    );
  }

  const userToken = getUserToken();

  const inserted = db
    .insert(comments)
    .values({
      videoId,
      userToken,
      username: username.slice(0, 100),
      text: text.slice(0, 2000),
      createdAt: new Date().toISOString(),
    })
    .returning()
    .get();

  return NextResponse.json(inserted, { status: 201 });
}
