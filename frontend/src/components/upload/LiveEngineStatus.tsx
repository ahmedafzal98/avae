"use client";

import { useTaskStatuses } from "@/hooks/useTaskStatus";
import { BarChart3, CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGES = [
  {
    key: "extracting",
    label: "Extracting",
    description: "Parsing document structure and OCR text recognition...",
  },
  {
    key: "querying",
    label: "Querying Databases",
    description: "Cross-referencing legal identifiers against HM Land Registry.",
  },
  {
    key: "verifying",
    label: "Verifying",
    description: "Final validity check and discrepancy report generation.",
  },
] as const;

function getActiveStage(status: string, progress: number): number {
  if (status === "FAILED" || status === "EXPIRED") return 0;
  if (
    status === "COMPLETED" ||
    status === "PENDING_HUMAN_REVIEW" ||
    status === "AWAITING_CLIENT_REMEDIATION"
  )
    return 3;
  if (status === "PENDING") return 0;
  if (progress < 25) return 0;
  if (progress < 50) return 1;
  if (progress < 75) return 2;
  return 3;
}

export interface LiveEngineStatusProps {
  taskIds: string[];
  className?: string;
}

export function LiveEngineStatus({ taskIds, className }: LiveEngineStatusProps) {
  const queries = useTaskStatuses(taskIds);

  const hasTasks = taskIds.length > 0;
  const firstTask = queries[0];
  const { data, isError, isLoading } = firstTask ?? {};
  const status = data?.status ?? "PENDING";
  const progress = data?.progress ?? 0;
  const activeStage = getActiveStage(status, progress);
  const isComplete =
    activeStage >= 3 ||
    status === "COMPLETED" ||
    status === "PENDING_HUMAN_REVIEW" ||
    status === "AWAITING_CLIENT_REMEDIATION";
  const showProgress =
    activeStage < 3 && (status === "PENDING" || status === "PROCESSING");

  if (!hasTasks) {
    return (
      <div
        className={cn(
          "rounded-lg border border-[#e2e8f0] bg-white p-4",
          className
        )}
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="size-4 text-[#64748b]" />
          <h3 className="text-sm font-semibold text-[#0f172a]">
            Live Engine Status
          </h3>
        </div>
        <p className="mt-2 text-xs text-[#64748b]">
          Upload files to see processing status
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-[#e2e8f0] bg-white p-4",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <BarChart3 className="size-4 text-[#64748b]" />
        <h3 className="text-sm font-semibold text-[#0f172a]">
          Live Engine Status
        </h3>
      </div>

      {/* Vertical stepper */}
      <div className="relative mt-4">
        {STAGES.map((stage, i) => {
          const isActive = activeStage === i;
          const isPast = activeStage > i;
          const isPending = !isActive && !isPast;
          const showStageProgress = isActive && showProgress;

          return (
            <div
              key={stage.key}
              className="relative flex gap-3 pb-6 last:pb-0"
            >
              {/* Step indicator + connector line */}
              <div className="relative flex flex-col items-center">
                <div
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                    isPast && "border-[#059669] bg-[#059669]",
                    isActive && "border-[#0f172a] bg-[#0f172a]",
                    isPending && "border-[#94a3b8] bg-white"
                  )}
                >
                  {isActive && showStageProgress ? (
                    <Loader2 className="size-3.5 animate-spin text-white" />
                  ) : isPast ? (
                    <CheckCircle2 className="size-3.5 text-white" />
                  ) : isActive ? (
                    <div className="size-2 rounded-full bg-white" />
                  ) : null}
                </div>
                {i < STAGES.length - 1 && (
                  <div
                    className={cn(
                      "absolute left-1/2 top-7 h-6 w-px -translate-x-px",
                      isPast ? "bg-[#059669]" : "bg-[#e2e8f0]"
                    )}
                  />
                )}
              </div>

              {/* Step content */}
              <div className="min-w-0 flex-1 pt-0.5">
                <p
                  className={cn(
                    "text-sm font-medium",
                    isActive || isPast
                      ? "text-[#0f172a]"
                      : "text-[#94a3b8]"
                  )}
                >
                  {stage.label}
                </p>
                <p
                  className={cn(
                    "mt-0.5 text-xs",
                    isActive || isPast
                      ? "text-[#64748b]"
                      : "text-[#94a3b8]"
                  )}
                >
                  {stage.description}
                </p>
                {showStageProgress && (
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#e2e8f0]">
                    <div
                      className="h-full rounded-full bg-[#0f172a] transition-all duration-300"
                      style={{
                        width: `${Math.min(
                          100,
                          ((progress - activeStage * 25) / 25) * 100
                        )}%`,
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Success card */}
      {hasTasks && (
        <div className="mt-4 rounded-lg border border-[#059669]/30 bg-[#ecfdf5] p-3">
          <div className="flex items-start gap-2">
            <CheckCircle2
              className="mt-0.5 size-4 shrink-0 text-[#059669]"
              aria-hidden
            />
            <div>
              <p className="text-sm font-semibold text-[#047857]">
                {isComplete ? "Upload Complete" : "Queued for Processing"}
              </p>
              <p className="mt-0.5 text-xs text-[#047857]/90">
                {isComplete
                  ? "Verification complete. Review in Dashboard."
                  : "Estimated completion: 14:02 GMT"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
