/**
 * Proxy GET /hitl/remediation-email/{checkpoint_id} (Task 6.5, 6.7)
 * Query param: message (optional)
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ checkpointId: string }> }
) {
  const { checkpointId } = await params;
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/hitl/remediation-email/${checkpointId}${search ? `?${search}` : ""}`;

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
    console.error("[api/hitl/remediation-email] Proxy error:", err);
    return NextResponse.json(
      { error: "Remediation email proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
