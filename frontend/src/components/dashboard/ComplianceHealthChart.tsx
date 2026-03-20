"use client";

import { useQueries } from "@tanstack/react-query";
import { getAuditLogsStats } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

function formatWeekLabel(d: Date): string {
  const month = d.toLocaleDateString("en-GB", { month: "short" });
  const day = d.getDate();
  return `${month} ${day}`;
}

export function ComplianceHealthChart() {
  const now = new Date();
  const weeks = Array.from({ length: 6 }, (_, i) => {
    const end = new Date(now);
    end.setDate(end.getDate() - i * 7);
    const start = new Date(end);
    start.setDate(start.getDate() - 6);
    return {
      key: `week-${i}`,
      label: formatWeekLabel(start),
      dateFrom: start.toISOString().slice(0, 10),
      dateTo: end.toISOString().slice(0, 10),
    };
  }).reverse();

  const queries = useQueries({
    queries: weeks.map((w) => ({
      queryKey: ["audit-stats", w.dateFrom, w.dateTo],
      queryFn: () => getAuditLogsStats({ date_from: w.dateFrom, date_to: w.dateTo }),
    })),
  });

  const bars = weeks.map((w, i) => {
    const data = queries[i]?.data;
    const value = data && data.total > 0 ? data.success_rate : 0;
    return { ...w, value, isLoading: queries[i]?.isLoading };
  });

  const isLoading = queries.some((q) => q.isLoading);
  const maxValue = Math.max(100, ...bars.map((b) => b.value));

  if (isLoading) {
    return (
      <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
          Compliance Health Index
        </p>
        <Skeleton className="mt-4 h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
        Compliance Health Index
      </p>
      <div className="mt-4 flex h-32 items-end gap-2">
        {bars.map((bar, i) => (
          <div key={bar.key} className="flex min-w-0 flex-1 flex-col items-center">
            <div
              className="w-full min-w-0 rounded-t-sm"
              style={{
                height: `${(bar.value / maxValue) * 100}%`,
                minHeight: "4px",
                backgroundColor: bar.value > 0 ? "#0f172a" : "#f1f5f9",
              }}
            />
            <span className="mt-1.5 text-[10px] font-medium text-[#64748b]">
              {bar.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
