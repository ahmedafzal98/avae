"use client";

import Link from "next/link";
import { useTaskStatuses } from "@/hooks/useTaskStatus";
import { BarChart3, CheckCircle2, Loader2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const PROCESSING_MESSAGES = [
  "Reading your document…",
  "Checking against official records…",
  "Preparing verification…",
] as const;

function getProcessingMessage(progress: number): string {
  if (progress < 33) return PROCESSING_MESSAGES[0];
  if (progress < 66) return PROCESSING_MESSAGES[1];
  return PROCESSING_MESSAGES[2];
}

function isComplete(status: string): boolean {
  return [
    "COMPLETED",
    "PENDING_HUMAN_REVIEW",
    "AWAITING_CLIENT_REMEDIATION",
  ].includes(status);
}

export interface LiveEngineStatusProps {
  taskIds: string[];
  className?: string;
}

export function LiveEngineStatus({ taskIds, className }: LiveEngineStatusProps) {
  const queries = useTaskStatuses(taskIds);
  const hasTasks = taskIds.length > 0;
  const firstTask = queries[0];
  const { data } = firstTask ?? {};
  const status = data?.status ?? "PENDING";
  const progress = data?.progress ?? 0;
  const documentId = taskIds[0];
  const complete = isComplete(status);
  const processing =
    status === "PENDING" || status === "PROCESSING";

  if (!hasTasks) {
    return (
      <div
        className={cn(
          "rounded-lg border border-[#e2e8f0] bg-white p-5",
          className
        )}
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="size-4 text-[#64748b]" />
          <h3 className="text-sm font-semibold text-[#0f172a]">
            Document Status
          </h3>
        </div>
        <p className="mt-2 text-sm text-[#64748b]">
          Upload a document to see its verification status here.
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-[#e2e8f0] bg-white p-5",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <BarChart3 className="size-4 text-[#64748b]" />
        <h3 className="text-sm font-semibold text-[#0f172a]">
          Document Status
        </h3>
      </div>

      {processing && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-4">
          <Loader2 className="size-5 shrink-0 animate-spin text-slate-500" />
          <div>
            <p className="text-sm font-medium text-slate-800">
              {getProcessingMessage(progress)}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              This usually takes a minute or two.
            </p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-slate-600 transition-all duration-500"
                style={{ width: `${Math.min(100, progress)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {complete && documentId && (
        <div className="mt-4 overflow-hidden rounded-lg border border-emerald-200 bg-emerald-50/80">
          <div className="flex items-start gap-3 p-4">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-emerald-100">
              <CheckCircle2 className="size-5 text-emerald-600" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-emerald-900">
                Verification complete
              </p>
              <p className="mt-1 text-xs text-emerald-700">
                Your document has been checked against official records. Review any differences and approve to continue.
              </p>
              <Link
                href={`/hitl?document_id=${documentId}`}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700"
              >
                Review Document
                <ArrowRight className="size-4" strokeWidth={2} />
              </Link>
            </div>
          </div>
        </div>
      )}

      {!processing && !complete && status !== "PENDING" && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/50 p-4">
          <p className="text-sm font-medium text-amber-800">
            {status === "FAILED" || status === "EXPIRED"
              ? "Processing did not complete"
              : "Waiting for processing…"}
          </p>
          <p className="mt-1 text-xs text-amber-700">
            {status === "FAILED" || status === "EXPIRED"
              ? "You may need to upload again."
              : "Your document is in the queue."}
          </p>
        </div>
      )}
    </div>
  );
}
