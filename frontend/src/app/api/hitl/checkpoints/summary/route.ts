/**
 * Proxy GET /hitl/checkpoints/summary (Phase 7.8).
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(request: NextRequest) {
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/hitl/checkpoints/summary`;

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
    console.error("[api/hitl/checkpoints/summary] Proxy error:", err);
    return NextResponse.json(
      { error: "Checkpoints summary proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
