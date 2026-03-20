"use client";

import { useQuery } from "@tanstack/react-query";
import { getAuditLogsStats } from "@/lib/api";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, Loader2, BarChart3 } from "lucide-react";

export interface AuditHealthIndexProps {
  /** Optional date range to scope stats (e.g. from audit page filters) */
  dateFrom?: string | null;
  dateTo?: string | null;
  className?: string;
}

/**
 * Phase 7.7: Audit Health Index card — global verification success rate and trend indicator.
 */
export function AuditHealthIndex({
  dateFrom,
  dateTo,
  className,
}: AuditHealthIndexProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-logs-stats", dateFrom ?? null, dateTo ?? null],
    queryFn: () =>
      getAuditLogsStats({
        date_from: dateFrom ?? undefined,
        date_to: dateTo ?? undefined,
      }),
  });

  if (error) {
    return (
      <div
        className={cn(
          "rounded-lg border border-border bg-muted/30 p-4",
          className
        )}
      >
        <h2 className="text-sm font-medium text-muted-foreground">
          Audit Health Index
        </h2>
        <p className="mt-1 text-sm text-destructive">
          Failed to load stats
        </p>
      </div>
    );
  }

  if (isLoading || data == null) {
    return (
      <div
        className={cn(
          "rounded-lg border border-border bg-muted/30 p-4",
          className
        )}
      >
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <BarChart3 className="size-4" aria-hidden />
          Audit Health Index
        </h2>
        <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading…
        </div>
      </div>
    );
  }

  const trendLabel =
    data.trend_direction === "up"
      ? `Up ${data.trend_value}% vs previous period`
      : data.trend_direction === "down"
        ? `Down ${data.trend_value}% vs previous period`
        : "Stable vs previous period";
  const trendColor =
    data.trend_direction === "up"
      ? "text-tertiary"
      : data.trend_direction === "down"
        ? "text-destructive"
        : "text-muted-foreground";

  const trendIcon =
    data.trend_direction === "up" ? (
      <TrendingUp className="size-3.5 shrink-0" aria-hidden />
    ) : data.trend_direction === "down" ? (
      <TrendingDown className="size-3.5 shrink-0" aria-hidden />
    ) : (
      <Minus className="size-3.5 shrink-0" aria-hidden />
    );

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-muted/30 flex flex-col gap-2 p-4",
        className
      )}
    >
      <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
        <BarChart3 className="size-4" aria-hidden />
        Audit Health Index
      </h2>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold tabular-nums text-foreground">
          {data.success_rate}%
        </span>
        <span className="text-sm text-muted-foreground">success rate</span>
      </div>
      <p className="text-xs text-muted-foreground">
        {data.verified} verified of {data.total} entries
      </p>
      <div
        className={cn(
          "flex items-center gap-1.5 text-xs font-medium",
          trendColor
        )}
      >
        {trendIcon}
        <span>{trendLabel}</span>
      </div>
    </div>
  );
}
