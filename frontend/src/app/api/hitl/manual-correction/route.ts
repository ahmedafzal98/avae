/**
 * Proxy POST /hitl/manual-correction (Task 6.4)
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function POST(request: NextRequest) {
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/hitl/manual-correction`;

  try {
    const headers = new Headers();
    request.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "host" && key.toLowerCase() !== "content-length") {
        headers.set(key, value);
      }
    });
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const res = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: request.body,
      duplex: "half",
    } as RequestInit);

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[api/hitl/manual-correction] Proxy error:", err);
    return NextResponse.json(
      { error: "Manual correction proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
