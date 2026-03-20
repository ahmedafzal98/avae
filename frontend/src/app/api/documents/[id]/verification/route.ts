/**
 * Proxy verification data from backend (Task 5.4).
 * GET /api/documents/43/verification → BACKEND_URL/documents/43/verification
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/documents/${id}/verification`;

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
    console.error("[api/documents/verification] Proxy error:", err);
    return NextResponse.json(
      { error: "Verification proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
