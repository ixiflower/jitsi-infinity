import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

const UPLOAD_DIR = path.join(process.cwd(), "..", "uploads");

export async function GET(_req: NextRequest, { params }: { params: { filename: string } }) {
  try {
    const filepath = path.join(UPLOAD_DIR, params.filename);
    const ext = params.filename.split(".").pop()?.toLowerCase();
    const mime: Record<string, string> = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", gif: "image/gif", webp: "image/webp" };
    const buf = await readFile(filepath);
    return new NextResponse(buf, { headers: { "Content-Type": mime[ext || ""] || "application/octet-stream", "Cache-Control": "public, max-age=31536000" } });
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
}
