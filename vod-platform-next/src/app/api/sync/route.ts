import { NextResponse } from "next/server";
import { execSync } from "child_process";
import { getAdminSession } from "../../../lib/auth";

export async function POST() {
  const isAdmin = await getAdminSession();
  if (!isAdmin) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const out = execSync("cd /home/ubuntu/jitsi-infinity && python3 scripts/sync-vods-to-db.py", {
      timeout: 60000,
      encoding: "utf-8",
    });
    return NextResponse.json({ success: true, output: out.trim() });
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "Sync failed" }, { status: 500 });
  }
}
