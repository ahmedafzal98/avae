/**
 * Proxy upload to backend — avoids CORS when frontend (localhost:3000)
 * sends credentialed requests to backend (localhost:8000).
 *
 * Forwards POST /api/upload → BACKEND_URL/upload
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/upload${search ? `?${search}` : ""}`;

  try {
    // Clone the request to forward body and headers (except host)
    const headers = new Headers();
    request.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "host" && key.toLowerCase() !== "content-length") {
        headers.set(key, value);
      }
    });

    const res = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: request.body,
      duplex: "half",
    } as RequestInit);

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[api/upload] Proxy error:", err);
    return NextResponse.json(
      { error: "Upload proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
