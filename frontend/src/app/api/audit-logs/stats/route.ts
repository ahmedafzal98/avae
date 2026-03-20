/**
 * Proxy GET /audit-logs/stats (Phase 7.7).
 * Query params: date_from, date_to (optional)
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/audit-logs/stats${search ? `?${search}` : ""}`;

  try {
    const authHeader = request.headers.get("authorization");
    const headers = new Headers();
    if (authHeader) headers.set("Authorization", authHeader);

    const res = await fetch(backendUrl, { headers });

    if (!res.ok) {
      const text = await res.text();
      let body: unknown;
      try {
        body = JSON.parse(text);
      } catch {
        body = { error: text || res.statusText };
      }
      return NextResponse.json(body, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("[api/audit-logs/stats] Proxy error:", err);
    return NextResponse.json(
      { error: "Audit stats proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
