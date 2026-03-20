/**
 * Proxy GET /audit-logs/{audit_log_id} (Phase 7.9 expand row).
 */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ auditLogId: string }> }
) {
  const { auditLogId } = await params;
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/audit-logs/${auditLogId}`;

  try {
    const authHeader = _request.headers.get("authorization");
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
    console.error("[api/audit-logs/[auditLogId]] Proxy error:", err);
    return NextResponse.json(
      { error: "Audit log detail proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
