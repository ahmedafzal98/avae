"use client";

import { useQuery } from "@tanstack/react-query";
import { getAuditLogsStats, getHitlCheckpointsSummary } from "@/lib/api";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { Skeleton } from "@/components/ui/skeleton";

function toYYYYMMDD(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function DashboardMetrics() {
  const today = new Date();
  const dateToday = toYYYYMMDD(today);

  const { data: statsToday, isLoading: loadingToday } = useQuery({
    queryKey: ["audit-stats-today", dateToday],
    queryFn: () =>
      getAuditLogsStats({ date_from: dateToday, date_to: dateToday }),
  });

  const { data: statsPeriod, isLoading: loadingPeriod } = useQuery({
    queryKey: ["audit-stats-period"],
    queryFn: () => getAuditLogsStats(),
  });

  const { data: checkpointSummary, isLoading: loadingCheckpoints } = useQuery({
    queryKey: ["hitl-checkpoints-summary"],
    queryFn: () => getHitlCheckpointsSummary(),
  });

  const isLoading = loadingToday || loadingPeriod || loadingCheckpoints;

  if (isLoading) {
    return (
      <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    );
  }

  const verificationsToday = statsToday?.total ?? 0;
  const pendingReview = (checkpointSummary?.pending_review ?? 0) + (checkpointSummary?.awaiting_client ?? 0);
  const complianceScore = statsPeriod?.success_rate ?? 0;
  const trendDirection = statsPeriod?.trend_direction ?? "stable";
  const trendValue = statsPeriod?.trend_value ?? 0;

  const totalInPeriod = statsPeriod?.total ?? 0;
  const trendLabel =
    trendDirection === "stable"
      ? "—"
      : trendDirection === "up"
        ? `+${trendValue}%`
        : `-${trendValue}%`;

  return (
    <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard label="Verifications Today" value={String(verificationsToday)} />
      <MetricCard label="Pending Review" value={String(pendingReview)} />
      <MetricCard
        label="Compliance Score"
        value={totalInPeriod > 0 ? `${complianceScore}%` : "—"}
        trend={
          trendDirection === "up" ? "up" : trendDirection === "down" ? "down" : undefined
        }
        trendLabel={
          trendDirection !== "stable" && totalInPeriod > 0 ? trendLabel : undefined
        }
      />
      <MetricCard label="Avg. Resolution" value="—" />
    </div>
  );
}
