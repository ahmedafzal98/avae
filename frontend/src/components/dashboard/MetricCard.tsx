"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MetricCardProps {
  label: string;
  value: string;
  trend?: "up" | "down";
  trendLabel?: string;
  className?: string;
}

export function MetricCard({
  label,
  value,
  trend,
  trendLabel,
  className,
}: MetricCardProps) {
  const showTrend = trend != null && trendLabel != null;
  const isUp = trend === "up";
  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6",
        className
      )}
    >
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
        {label}
      </p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-[30px] font-bold leading-none text-[#0f172a]">
          {value}
        </span>
        {showTrend && (
          <span
            className={cn(
              "flex items-center gap-0.5 text-xs font-medium",
              isUp ? "text-[#059669]" : "text-[#dc2626]"
            )}
          >
            {isUp ? (
              <TrendingUp className="size-3.5" strokeWidth={1.5} aria-hidden />
            ) : (
              <TrendingDown className="size-3.5" strokeWidth={1.5} aria-hidden />
            )}
            {trendLabel}
          </span>
        )}
      </div>
    </div>
  );
}
