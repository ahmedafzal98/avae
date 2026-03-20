/**
 * Proxy PDF from backend — avoids CORS when Viewer fetches PDF.
 * GET /api/documents/43/pdf → BACKEND_URL/documents/43/pdf
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
  const backendUrl = `${BACKEND_URL.replace(/\/$/, "")}/documents/${id}/pdf`;

  try {
    const authHeader = request.headers.get("authorization");
    const headers = new Headers();
    if (authHeader) headers.set("Authorization", authHeader);

    const res = await fetch(backendUrl, { headers });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: text || res.statusText },
        { status: res.status }
      );
    }

    const blob = await res.blob();
    return new NextResponse(blob, {
      status: 200,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/pdf",
        "Content-Disposition":
          res.headers.get("Content-Disposition") || "inline",
      },
    });
  } catch (err) {
    console.error("[api/documents/pdf] Proxy error:", err);
    return NextResponse.json(
      { error: "PDF proxy failed", detail: String(err) },
      { status: 502 }
    );
  }
}
