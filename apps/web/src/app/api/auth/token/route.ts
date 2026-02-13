import { NextRequest, NextResponse } from "next/server";

/**
 * Returns the raw JWT string for the frontend API client
 * to include in Authorization: Bearer headers.
 */
export async function GET(req: NextRequest) {
  const cookieNames = [
    "__Secure-authjs.session-token",
    "__Host-authjs.session-token",
    "authjs.session-token",
    "__Secure-next-auth.session-token",
    "next-auth.session-token",
  ];

  const token =
    cookieNames
      .map((name) => req.cookies.get(name)?.value)
      .find((v) => typeof v === "string" && v.length > 0) ?? null;

  const headers = {
    "Cache-Control": "no-store, max-age=0",
  };

  if (!token) {
    return NextResponse.json(
      { error: "Not authenticated" },
      { status: 401, headers }
    );
  }

  return NextResponse.json({ token }, { headers });
}
