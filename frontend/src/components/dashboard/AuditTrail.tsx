"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getAuditLogs } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function statusToAction(status: string): string {
  const map: Record<string, string> = {
    VERIFIED: "Verification completed",
    DISCREPANCY_FLAG: "Discrepancy flagged",
    PENDING_HUMAN_REVIEW: "Pending human review",
    AWAITING_CLIENT_REMEDIATION: "Awaiting client remediation",
    COMPLETED: "Processing completed",
    PENDING: "Document queued",
  };
  return map[status] ?? status;
}

export function AuditTrail() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-logs-recent"],
    queryFn: () => getAuditLogs({ page: 1, page_size: 5 }),
  });

  const items = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
          Audit Trail
        </p>
        <Skeleton className="mt-4 h-32 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
          Audit Trail
        </p>
        <p className="mt-4 text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load"}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
        Audit Trail
      </p>
      <div className="mt-4">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No audit entries yet. Upload a document to get started.
          </p>
        ) : (
          items.map((event, i) => (
            <div
              key={event.id}
              className="relative flex gap-3 pb-4 last:pb-0"
            >
              {i < items.length - 1 && (
                <div
                  className="absolute left-[5px] top-5 h-[calc(100%-8px)] w-px bg-[#e2e8f0]"
                  aria-hidden
                />
              )}
              <div className="relative z-10 flex size-2.5 shrink-0 rounded-full bg-[#0f172a]" />
              <div className="min-w-0 flex-1">
                <p className="font-mono text-xs text-[#0f172a]">
                  <Link
                    href={`/hitl?document_id=${event.document_id}`}
                    className="hover:underline"
                  >
                    DOC-{event.document_id}
                  </Link>{" "}
                  <span className="text-[#64748b]">// {formatTime(event.created_at)}</span>
                </p>
                <p className="mt-0.5 text-xs text-[#64748b]">
                  {statusToAction(event.verification_status)} — {event.filename}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
