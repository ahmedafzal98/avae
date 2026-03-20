"use client";

import { useQueries } from "@tanstack/react-query";
import { getAuditLogsStats } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

function formatDayLabel(d: Date): string {
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric" });
}

export function InstancePerformance() {
  const now = new Date();
  const days = Array.from({ length: 6 }, (_, i) => {
    const end = new Date(now);
    end.setDate(end.getDate() - i);
    const start = new Date(end);
    start.setDate(start.getDate());
    return {
      key: `day-${i}`,
      label: formatDayLabel(end),
      dateFrom: end.toISOString().slice(0, 10),
      dateTo: end.toISOString().slice(0, 10),
    };
  }).reverse();

  const queries = useQueries({
    queries: days.map((d) => ({
      queryKey: ["instance-perf", d.dateFrom, d.dateTo],
      queryFn: () =>
        getAuditLogsStats({ date_from: d.dateFrom, date_to: d.dateTo }),
    })),
  });

  const bars = days.map((d, i) => {
    const data = queries[i]?.data;
    const value = data && data.total > 0 ? data.success_rate : 0;
    return { ...d, value };
  });

  const isLoading = queries.some((q) => q.isLoading);
  const last7DaysTotal = queries.reduce(
    (sum, q) => sum + (q.data?.total ?? 0),
    0
  );
  const last7DaysVerified = queries.reduce(
    (sum, q) => sum + (q.data?.verified ?? 0),
    0
  );
  const successRate =
    last7DaysTotal > 0
      ? Math.round((100 * last7DaysVerified) / last7DaysTotal)
      : 0;
  const maxValue = Math.max(100, ...bars.map((b) => b.value));

  if (isLoading) {
    return (
      <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-5 font-sans">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
          Instance Performance
        </p>
        <Skeleton className="mt-3 h-8 w-24" />
        <Skeleton className="mt-4 h-10 w-full" />
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-5 font-sans">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
        Instance Performance
      </p>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-[#0f172a]">{successRate}%</span>
        <span className="text-xs font-medium text-muted-foreground">
          Verification success (last 6 days)
        </span>
      </div>
      <div className="mt-4 flex h-10 min-w-0 items-end gap-1">
        {bars.map((bar) => (
          <div
            key={bar.key}
            className="min-w-0 flex-1 rounded-t-sm"
            style={{
              height: `${(bar.value / maxValue) * 100}%`,
              minHeight: "4px",
              backgroundColor: bar.value > 0 ? "#0f172a" : "#e2e8f0",
            }}
          />
        ))}
      </div>
    </div>
  );
}
