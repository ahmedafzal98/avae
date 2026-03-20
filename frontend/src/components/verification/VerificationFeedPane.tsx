"use client";

import { CheckCircle, AlertTriangle, Flag, RotateCcw } from "lucide-react";
import type { VerificationFieldRow } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

function formatFieldName(field: string): string {
  return field
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "string") return val;
  if (typeof val === "number" || typeof val === "boolean") return String(val);
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export interface VerificationFeedPaneProps {
  /** Batch/document ID for header */
  batchId?: string | null;
  rows: VerificationFieldRow[];
  isLoading?: boolean;
  error?: string | null;
  onConfirmCorrect?: () => void;
  onFlagForReview?: () => void;
  onReExtract?: () => void;
  onDiscrepancyCardClick?: (row: VerificationFieldRow) => void;
  /** Called when user hovers or clicks a row — triggers PDF highlight (red/green) */
  onRowHighlight?: (row: VerificationFieldRow | null) => void;
  /** Currently highlighted row (for visual feedback) */
  highlightedRow?: VerificationFieldRow | null;
  className?: string;
}

/**
 * Professional Verification Feed — card-based layout for compliance officers.
 * Sovereign Terminal aesthetic: Inter (UI), JetBrains Mono (Batch ID).
 */
export function VerificationFeedPane({
  batchId,
  rows,
  isLoading = false,
  error = null,
  onConfirmCorrect,
  onFlagForReview,
  onReExtract,
  onDiscrepancyCardClick,
  onRowHighlight,
  highlightedRow,
  className,
}: VerificationFeedPaneProps) {
  const verified = rows.filter((r) => r.status === "VERIFIED").length;
  const discrepancies = rows.filter((r) => r.status === "DISCREPANCY").length;
  const total = rows.length;
  const confidence =
    total > 0 ? ((verified / total) * 100).toFixed(1) : null;

  if (error) {
    return (
      <div
        className={cn(
          "flex flex-1 flex-col items-center justify-center rounded-lg border border-slate-200 bg-white p-8",
          className
        )}
      >
        <p className="text-sm text-[#dc2626]">{error}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white",
        className
      )}
    >
      {/* Header: Verification Summary + Batch ID + Confidence Gauge */}
      <div className="shrink-0 border-b border-slate-200 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Verification Summary
            </h2>
            {batchId && (
              <p className="mt-1 font-mono text-sm text-slate-500">
                Batch ID: {batchId}
              </p>
            )}
          </div>
          {isLoading ? (
            <Skeleton className="h-14 w-32 rounded-lg" />
          ) : confidence != null ? (
            <div className="flex flex-col items-center sm:items-end">
              <span className="text-3xl font-bold tabular-nums text-slate-900">
                {confidence}%
              </span>
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Confidence
              </span>
            </div>
          ) : null}
        </div>
      </div>

      {/* Alert: Attention Required */}
      {!isLoading && discrepancies > 0 && (
        <div
          className="shrink-0 border-b border-slate-200 bg-rose-50/80 px-6 py-3"
          role="alert"
        >
          <p className="flex items-center gap-2 text-sm font-medium text-rose-700">
            <AlertTriangle className="size-4 shrink-0" strokeWidth={1.5} />
            Attention Required: {discrepancies} Discrepancy
            {discrepancies !== 1 ? "ies" : ""} found
          </p>
          {onDiscrepancyCardClick && (
            <p className="mt-1 text-xs text-rose-600">
              Click a discrepancy card to open resolution options.
            </p>
          )}
        </div>
      )}

      {/* Comparison Cards */}
      <div className="min-h-0 flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-6"
              >
                <Skeleton className="mb-4 h-4 w-24" />
                <div className="grid grid-cols-2 gap-4">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
              </div>
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No verification data available
          </p>
        ) : (
          <div className="space-y-4">
            {rows.map((row, idx) => (
              <ComparisonCard
                key={`${row.field}-${idx}`}
                row={row}
                onClick={
                  row.status === "DISCREPANCY" && onDiscrepancyCardClick
                    ? () => onDiscrepancyCardClick(row)
                    : undefined
                }
                onHighlight={onRowHighlight}
                isHighlighted={
                  highlightedRow != null &&
                  highlightedRow.field === row.field &&
                  highlightedRow.document_value === row.document_value
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Sticky Footer Actions */}
      <div className="shrink-0 border-t border-slate-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={onReExtract}
            disabled={!onReExtract}
            className="gap-1.5 border-slate-200 font-medium text-slate-700 hover:bg-slate-50"
          >
            <RotateCcw className="size-4" strokeWidth={1.5} />
            Re-extract Field
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onFlagForReview}
            disabled={!onFlagForReview}
            className="gap-1.5 border-rose-200 bg-rose-50/50 font-medium text-rose-700 hover:bg-rose-100"
          >
            <Flag className="size-4" strokeWidth={1.5} />
            Flag for Review
          </Button>
          <Button
            size="sm"
            onClick={onConfirmCorrect}
            disabled={!onConfirmCorrect}
            className="gap-1.5 bg-slate-900 font-medium text-white hover:bg-slate-800"
          >
            <CheckCircle className="size-4" strokeWidth={1.5} />
            Confirm as Correct
          </Button>
        </div>
      </div>
    </div>
  );
}

function ComparisonCard({
  row,
  onClick,
  onHighlight,
  isHighlighted,
}: {
  row: VerificationFieldRow;
  onClick?: () => void;
  onHighlight?: (row: VerificationFieldRow | null) => void;
  isHighlighted?: boolean;
}) {
  const isMatch = row.status === "VERIFIED";
  const isDiscrepancy = row.status === "DISCREPANCY";
  const isPending = row.status === "PENDING";
  const hasPdfLocation = !!row.pdf_location;

  const handleClick = () => {
    if (onClick) onClick();
    if (onHighlight && hasPdfLocation) {
      onHighlight(isHighlighted ? null : row);
    }
  };

  const handleMouseEnter = () => {
    if (onHighlight && hasPdfLocation) onHighlight(row);
  };

  const handleMouseLeave = () => {
    if (onHighlight) onHighlight(null);
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 bg-white p-6 transition-colors",
        isMatch && "border-l-4 border-l-emerald-500",
        isDiscrepancy && "border-l-4 border-l-rose-500",
        isPending && "border-l-4 border-l-slate-300",
        (isDiscrepancy && onClick) || (onHighlight && hasPdfLocation) ? "cursor-pointer" : "",
        (isDiscrepancy && onClick) || (onHighlight && hasPdfLocation) ? "hover:bg-slate-50/80" : "",
        isHighlighted && "ring-2 ring-slate-400 ring-offset-2",
        onHighlight && !hasPdfLocation && "opacity-90"
      )}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role={(isDiscrepancy && onClick) || (onHighlight && hasPdfLocation) ? "button" : undefined}
      tabIndex={(isDiscrepancy && onClick) || (onHighlight && hasPdfLocation) ? 0 : undefined}
      onKeyDown={
        (isDiscrepancy && onClick) || (onHighlight && hasPdfLocation)
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                if (onClick) onClick();
                if (onHighlight && hasPdfLocation) {
                  onHighlight(isHighlighted ? null : row);
                }
              }
            }
          : undefined
      }
    >
      <div>
        {/* Field name + Status Badge */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-slate-600">
            {formatFieldName(row.field)}
          </span>
          {isMatch && (
            <span className="inline-flex items-center gap-1 rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-700">
              <CheckCircle className="size-3" strokeWidth={1.5} />
              VERIFIED MATCH
            </span>
          )}
          {isDiscrepancy && (
            <span className="inline-flex items-center gap-1 rounded bg-rose-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-700">
              <AlertTriangle className="size-3" strokeWidth={1.5} />
              DISCREPANCY DETECTED
            </span>
          )}
          {isPending && (
            <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-600">
              PENDING
            </span>
          )}
        </div>

        {/* 2-column: FOUND IN DOCUMENT vs SYSTEM RECORD */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Found in Document
            </p>
            <p className="font-semibold text-slate-900">
              {formatValue(row.document_value)}
            </p>
          </div>
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              System Record
            </p>
            <p className="font-semibold text-slate-900">
              {formatValue(row.api_value)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
