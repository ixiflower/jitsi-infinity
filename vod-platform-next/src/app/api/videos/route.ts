import { NextRequest, NextResponse } from "next/server";
import { db } from "../../../db";
import { videos, videos as v } from "../../../db/schema";
import { getAdminSession } from "../../../lib/auth";
import { desc, eq } from "drizzle-orm";

// GET /api/videos -- return visible videos from local DB (public)
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const excludeId = searchParams.get("exclude");

  let rows = db
    .select()
    .from(v)
    .where(eq(v.visible, 1))
    .orderBy(desc(v.createdAt))
    .all();

  if (excludeId) {
    const numId = parseInt(excludeId, 10);
    if (!isNaN(numId)) {
      rows = rows.filter((r: any) => r.id !== numId);
    }
  }

  return NextResponse.json(rows);
}

// POST /api/videos -- add a new video (admin only, local DB)
export async function POST(req: NextRequest) {
  const isAdmin = await getAdminSession();
  if (!isAdmin) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { title?: string; player_url?: string; hls_url?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { title, player_url, hls_url } = body;
  if (!title || !player_url) {
    return NextResponse.json(
      { error: "title and player_url are required" },
      { status: 400 }
    );
  }

  const inserted = db
    .insert(videos)
    .values({
      title,
      playerUrl: player_url,
      hlsUrl: hls_url || "",
      visible: 1,
      createdAt: new Date().toISOString(),
    })
    .returning()
    .get();

  return NextResponse.json(inserted, { status: 201 });
}
