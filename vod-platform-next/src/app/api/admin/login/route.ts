import { NextRequest, NextResponse } from "next/server";
import { db } from "../../../../db";
import { admins } from "../../../../db/schema";
import { eq } from "drizzle-orm";
import { verifyPassword, createAdminToken, setAdminCookie } from "../../../../lib/auth";

// POST /api/admin/login — verify credentials and set admin cookie
export async function POST(req: NextRequest) {
  let body: { username?: string; password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { success: false, error: "Invalid JSON" },
      { status: 400 }
    );
  }

  const { username, password } = body;
  if (!username || !password) {
    return NextResponse.json(
      { success: false, error: "Username and password are required" },
      { status: 400 }
    );
  }

  // Look up admin
  const admin = db
    .select()
    .from(admins)
    .where(eq(admins.username, username))
    .get();

  if (!admin || !verifyPassword(password, admin.passwordHash)) {
    return NextResponse.json(
      { success: false, error: "Invalid credentials" },
      { status: 401 }
    );
  }

  // Create and set cookie
  const token = await createAdminToken(admin.username);
  await setAdminCookie(token);

  return NextResponse.json({ success: true });
}
