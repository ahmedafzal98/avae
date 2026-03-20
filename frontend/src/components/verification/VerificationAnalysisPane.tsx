"use client";

import { VerificationTable } from "./VerificationTable";
import type { VerificationFieldRow } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface VerificationAnalysisPaneProps {
  rows: VerificationFieldRow[];
  isLoading?: boolean;
  error?: string | null;
  onDiscrepancyRowClick?: (row: VerificationFieldRow) => void;
  className?: string;
}

export function VerificationAnalysisPane({
  rows,
  isLoading = false,
  error = null,
  onDiscrepancyRowClick,
  className,
}: VerificationAnalysisPaneProps) {
  const hasDiscrepancy = rows.some((r) => r.status === "DISCREPANCY");

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border border-[#e2e8f0] bg-white",
        className
      )}
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between gap-4 border-b border-[#e2e8f0] px-6 py-4">
        <h2 className="text-lg font-semibold text-[#0f172a]">
          Verification Analysis
        </h2>
        {hasDiscrepancy && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#dc2626]/15 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#dc2626]">
            Discrepancy Detected
          </span>
        )}
      </div>

      {/* Table */}
      <div className="min-h-0 flex-1 overflow-auto p-6">
        <VerificationTable
          rows={rows}
          isLoading={isLoading}
          error={error}
          onDiscrepancyRowClick={onDiscrepancyRowClick}
        />
      </div>
    </div>
  );
}
