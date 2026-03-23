"use client";

import { CheckCircle, AlertTriangle, BarChart3 } from "lucide-react";
import type { VerificationFieldRow } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface VerificationMetricsHeaderProps {
  rows: VerificationFieldRow[];
  isLoading?: boolean;
  className?: string;
}

/** Task 5.6: Metrics header — Confidence Score, Verified Fields (14/16), Discrepancies (1) */
export function VerificationMetricsHeader({
  rows,
  isLoading = false,
  className,
}: VerificationMetricsHeaderProps) {
  const verified = rows.filter((r) => r.status === "VERIFIED").length;
  const discrepancies = rows.filter((r) => r.status === "DISCREPANCY").length;
  const total = rows.length;
  const confidence =
    total > 0 ? Math.round((verified / total) * 100) : null;

  if (isLoading || total === 0) {
    return (
      <div
        className={cn(
          "flex shrink-0 items-center gap-6 border-b border-border bg-muted/20 px-4 py-3",
          className
        )}
      >
        <MetricItem
          icon={BarChart3}
          label="Reliability level"
          value={isLoading ? "…" : "—"}
        />
        <MetricItem
          icon={CheckCircle}
          label="Verified Fields"
          value={isLoading ? "…" : "—"}
        />
        <MetricItem
          icon={AlertTriangle}
          label="Differences found"
          value={isLoading ? "…" : "—"}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex shrink-0 items-center gap-6 border-b border-border bg-muted/20 px-4 py-3",
        className
      )}
    >
      <MetricItem
        icon={BarChart3}
        label="Reliability level"
        value={confidence != null ? `${confidence}%` : "—"}
        valueClassName={
          confidence != null && confidence >= 80
            ? "text-tertiary"
            : confidence != null && confidence < 50
              ? "text-destructive"
              : undefined
        }
      />
      <MetricItem
        icon={CheckCircle}
        label="Verified Fields"
        value={`${verified}/${total}`}
        valueClassName="text-tertiary"
      />
      <MetricItem
        icon={AlertTriangle}
        label="Differences found"
        value={String(discrepancies)}
        valueClassName={discrepancies > 0 ? "text-amber-600" : undefined}
      />
    </div>
  );
}

function MetricItem({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: typeof BarChart3;
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" aria-hidden />
      <span className="text-sm text-muted-foreground">{label}:</span>
      <span
        className={cn(
          "text-sm font-semibold tabular-nums",
          valueClassName ?? "text-foreground"
        )}
      >
        {value}
      </span>
    </div>
  );
}
