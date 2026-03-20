/**
 * Proxy POST /documents/{id}/requeue (Task 5.7 Re-run Extraction)
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/documents/${id}/requeue`;

  try {
    const authHeader = request.headers.get("authorization");
    const headers = new Headers();
    if (authHeader) headers.set("Authorization", authHeader);

    const res = await fetch(backendUrl, { method: "POST", headers });

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[api/documents/requeue] Proxy error:", err);
    return NextResponse.json(
      { error: "Requeue proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
