import { NextResponse } from "next/server";
import { clearAdminCookie } from "../../../../lib/auth";

// POST /api/admin/logout — clear admin cookie
export async function POST() {
  await clearAdminCookie();
  return NextResponse.json({ success: true });
}
