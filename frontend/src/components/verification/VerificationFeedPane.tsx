"use client";

import { useState } from "react";
import { CheckCircle, AlertTriangle, Flag, RotateCcw, ShieldCheck, HelpCircle } from "lucide-react";
import type { VerificationFieldRow } from "@/lib/api";
import {
  getOfficialRegistryName,
  getSourceBadgeLabel,
  getSourceBadgeEmoji,
  formatLiveSyncTimestamp,
} from "@/lib/registry-labels";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ExtractedValue } from "@/components/verification/ExtractedValue";
import {
  buildVisionPocDisplayItems,
  visionPocFieldLabelArabic,
  type VisionPocDisplayItem,
} from "@/lib/vision-poc-display";

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
  /** Document reference for header (e.g. document ID) */
  batchId?: string | null;
  /** Audit target (companies_house, epc, etc.) — used to display registry name */
  auditTarget?: string | null;
  /** Backend verification status (e.g. EXTRACTED = no registry compare) */
  verificationStatus?: string | null;
  /** ISO timestamp when official registry was last synced */
  officialRecordSyncedAt?: string | null;
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
  auditTarget,
  verificationStatus,
  officialRecordSyncedAt,
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
  /** Vision POC / financial-style: extraction only, no Companies House (etc.) column */
  const extractionOnly =
    auditTarget === "vision_poc" || verificationStatus === "EXTRACTED";

  /** Bilingual EN/AR layout for vision POC name fields */
  const visionPocBilingual = auditTarget === "vision_poc";
  const displayItems = visionPocBilingual
    ? buildVisionPocDisplayItems(rows)
    : null;

  const verified = extractionOnly
    ? rows.filter(
        (r) =>
          r.document_value != null && String(r.document_value).trim() !== ""
      ).length
    : rows.filter((r) => r.status === "VERIFIED").length;
  const differences = rows.filter((r) => r.status === "DISCREPANCY").length;
  const total = rows.length;
  const reliability =
    total > 0
      ? extractionOnly
        ? ((verified / total) * 100).toFixed(1)
        : ((rows.filter((r) => r.status === "VERIFIED").length / total) * 100).toFixed(1)
      : null;

  // Overall Status: Low / Medium / High Risk (executive-friendly)
  const overallStatus =
    extractionOnly && differences === 0
      ? "low"
      : differences === 0
        ? "low"
        : differences <= 2
          ? "medium"
          : "high";

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
      {/* Top-Level Verification Summary (executives love this) */}
      <div className="shrink-0 border-b border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900">
          {extractionOnly ? "Extraction summary" : "Verification Summary"}
        </h2>
        {extractionOnly && (
          <p className="mt-1 text-sm text-slate-600">
            No external registry comparison for this mode — review extracted
            values against the PDF.
          </p>
        )}
        {batchId && (
          <p className="mt-1 font-mono text-sm text-slate-500">
            Reference: {batchId}
          </p>
        )}
        {isLoading ? (
          <Skeleton className="mt-4 h-16 w-full rounded-lg" />
        ) : total > 0 ? (
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <span className="inline-flex items-center gap-2 text-sm text-emerald-700">
              <CheckCircle className="size-4" strokeWidth={1.5} />
              <strong>{verified}</strong>{" "}
              {extractionOnly ? "fields with values" : "fields verified"}
            </span>
            {!extractionOnly && differences > 0 && (
              <span className="inline-flex items-center gap-2 text-sm text-amber-700">
                <AlertTriangle className="size-4" strokeWidth={1.5} />
                <strong>{differences}</strong> difference{differences !== 1 ? "s" : ""} found
              </span>
            )}
            <span
              className={cn(
                "ml-auto rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider",
                overallStatus === "low" && "bg-emerald-100 text-emerald-700",
                overallStatus === "medium" && "bg-amber-100 text-amber-700",
                overallStatus === "high" && "bg-rose-100 text-rose-700"
              )}
            >
              {overallStatus === "low" && "🟢 Low Risk"}
              {overallStatus === "medium" && "🟡 Medium Risk"}
              {overallStatus === "high" && "🔴 High Risk"}
            </span>
          </div>
        ) : null}
        {!isLoading && reliability != null && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-sm font-medium text-slate-600">
              Reliability
            </span>
            <span
              className={cn(
                "rounded-md px-2.5 py-0.5 text-sm font-bold tabular-nums",
                Number(reliability) >= 80 && "bg-emerald-100 text-emerald-800",
                Number(reliability) >= 50 && Number(reliability) < 80 && "bg-amber-100 text-amber-800",
                Number(reliability) < 50 && "bg-rose-100 text-rose-800"
              )}
            >
              {reliability}%
            </span>
          </div>
        )}
      </div>

      {/* Alert: Action Required when differences found */}
      {!isLoading && !extractionOnly && differences > 0 && (
        <div
          className="shrink-0 border-b border-slate-200 bg-amber-50/80 px-6 py-3"
          role="alert"
        >
          <p className="flex items-center gap-2 text-sm font-medium text-amber-700">
            <AlertTriangle className="size-4 shrink-0" strokeWidth={1.5} />
            Action Required: {differences} difference{differences !== 1 ? "s" : ""} found
          </p>
          {onDiscrepancyCardClick && (
            <p className="mt-1 text-xs text-amber-600">
              Click a difference to open resolution options.
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
            {visionPocBilingual && displayItems
              ? displayItems.map((item, idx) =>
                  item.kind === "single" ? (
                    <ComparisonCard
                      key={`${item.row.field}-${idx}`}
                      row={item.row}
                      extractionOnly={extractionOnly}
                      bilingualExtractedDisplay
                      registryName={getOfficialRegistryName(auditTarget ?? "")}
                      sourceBadge={getSourceBadgeLabel(auditTarget ?? "")}
                      sourceEmoji={getSourceBadgeEmoji(auditTarget ?? "")}
                      syncedAt={officialRecordSyncedAt}
                      onClick={
                        item.row.status === "DISCREPANCY" &&
                        onDiscrepancyCardClick
                          ? () => onDiscrepancyCardClick(item.row)
                          : undefined
                      }
                      onHighlight={onRowHighlight}
                      isHighlighted={
                        highlightedRow != null &&
                        highlightedRow.field === item.row.field &&
                        highlightedRow.document_value === item.row.document_value
                      }
                    />
                  ) : (
                    <BilingualPairCard
                      key={item.key}
                      item={item}
                      extractionOnly={extractionOnly}
                      onDiscrepancyCardClick={onDiscrepancyCardClick}
                      onHighlight={onRowHighlight}
                      highlightedRow={highlightedRow}
                    />
                  )
                )
              : rows.map((row, idx) => (
                  <ComparisonCard
                    key={`${row.field}-${idx}`}
                    row={row}
                    extractionOnly={extractionOnly}
                    bilingualExtractedDisplay={false}
                    registryName={getOfficialRegistryName(auditTarget ?? "")}
                    sourceBadge={getSourceBadgeLabel(auditTarget ?? "")}
                    sourceEmoji={getSourceBadgeEmoji(auditTarget ?? "")}
                    syncedAt={officialRecordSyncedAt}
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
            Approve & Continue
          </Button>
        </div>
      </div>
    </div>
  );
}

const WHY_DIFFERENT_EXPLANATION = `This difference may be due to:
• Different reporting period
• Recent update not yet reflected in official records
• Rounding or formatting differences`;

function rowHasPdfLocation(row: VerificationFieldRow | undefined): boolean {
  return !!row?.pdf_location;
}

function BilingualPairCard({
  item,
  extractionOnly,
  onDiscrepancyCardClick,
  onHighlight,
  highlightedRow,
}: {
  item: Extract<
    VisionPocDisplayItem,
    { kind: "name_pair" | "party_pair" }
  >;
  extractionOnly: boolean;
  onDiscrepancyCardClick?: (row: VerificationFieldRow) => void;
  onHighlight?: (row: VerificationFieldRow | null) => void;
  highlightedRow?: VerificationFieldRow | null;
}) {
  const { english, arabic, label, labelAr } = item;
  const primaryForHighlight =
    rowHasPdfLocation(english) ? english : rowHasPdfLocation(arabic) ? arabic : english ?? arabic;
  const hasPdfLocation = rowHasPdfLocation(english) || rowHasPdfLocation(arabic);

  const isHighlighted =
    highlightedRow != null &&
    ((english != null &&
      highlightedRow.field === english.field &&
      highlightedRow.document_value === english.document_value) ||
      (arabic != null &&
        highlightedRow.field === arabic.field &&
        highlightedRow.document_value === arabic.document_value));

  const handleClick = () => {
    const discrepancy =
      english?.status === "DISCREPANCY"
        ? english
        : arabic?.status === "DISCREPANCY"
          ? arabic
          : null;
    if (discrepancy && onDiscrepancyCardClick) {
      onDiscrepancyCardClick(discrepancy);
    }
    if (onHighlight && hasPdfLocation && primaryForHighlight) {
      onHighlight(isHighlighted ? null : primaryForHighlight);
    }
  };

  const handleMouseEnter = () => {
    if (onHighlight && primaryForHighlight && hasPdfLocation) {
      onHighlight(primaryForHighlight);
    }
  };

  const handleMouseLeave = () => {
    if (onHighlight) onHighlight(null);
  };

  const showExtractedBadge =
    extractionOnly &&
    ((english != null &&
      String(english.document_value ?? "").trim() !== "") ||
      (arabic != null && String(arabic.document_value ?? "").trim() !== ""));

  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 bg-white p-6 transition-colors",
        onHighlight && hasPdfLocation ? "cursor-pointer hover:bg-slate-50/80" : "",
        isHighlighted && "ring-2 ring-slate-400 ring-offset-2",
        onHighlight && !hasPdfLocation && "opacity-90"
      )}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role={onHighlight && hasPdfLocation ? "button" : undefined}
      tabIndex={onHighlight && hasPdfLocation ? 0 : undefined}
      onKeyDown={
        onHighlight && hasPdfLocation
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                if (primaryForHighlight) {
                  onHighlight?.(isHighlighted ? null : primaryForHighlight);
                }
              }
            }
          : undefined
      }
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
          <span className="text-sm font-semibold text-slate-800">{label}</span>
          <span
            className="text-sm font-medium text-slate-600"
            dir="rtl"
            lang="ar"
          >
            {labelAr}
          </span>
        </div>
        {showExtractedBadge && (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-800">
            Extracted
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="min-w-0">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            English
          </p>
          {english ? (
            <ExtractedValue field={english.field} value={english.document_value} />
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </div>
        <div className="min-w-0 border-t border-slate-100 pt-4 sm:border-t-0 sm:border-s sm:border-slate-100 sm:ps-6 sm:pt-0">
          <p
            className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500"
            dir="rtl"
          >
            العربية
          </p>
          {arabic ? (
            <ExtractedValue field={arabic.field} value={arabic.document_value} />
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

function ComparisonCard({
  row,
  extractionOnly = false,
  bilingualExtractedDisplay = false,
  registryName,
  sourceBadge,
  sourceEmoji,
  syncedAt,
  onClick,
  onHighlight,
  isHighlighted,
}: {
  row: VerificationFieldRow;
  extractionOnly?: boolean;
  /** Use RTL/LTR + Arabic font for vision_poc single fields */
  bilingualExtractedDisplay?: boolean;
  registryName: string;
  sourceBadge: string;
  sourceEmoji: string;
  syncedAt?: string | null;
  onClick?: () => void;
  onHighlight?: (row: VerificationFieldRow | null) => void;
  isHighlighted?: boolean;
}) {
  const [showWhyDifferent, setShowWhyDifferent] = useState(false);
  const isMatch = row.status === "VERIFIED";
  const isDifference = row.status === "DISCREPANCY";
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
        isDifference && "border-l-4 border-l-amber-500",
        isPending && "border-l-4 border-l-slate-300",
        (isDifference && onClick) || (onHighlight && hasPdfLocation) ? "cursor-pointer" : "",
        (isDifference && onClick) || (onHighlight && hasPdfLocation) ? "hover:bg-slate-50/80" : "",
        isHighlighted && "ring-2 ring-slate-400 ring-offset-2",
        onHighlight && !hasPdfLocation && "opacity-90"
      )}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role={(isDifference && onClick) || (onHighlight && hasPdfLocation) ? "button" : undefined}
      tabIndex={(isDifference && onClick) || (onHighlight && hasPdfLocation) ? 0 : undefined}
      onKeyDown={
        (isDifference && onClick) || (onHighlight && hasPdfLocation)
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
          {bilingualExtractedDisplay &&
          visionPocFieldLabelArabic(row.field) != null ? (
            <div className="flex min-w-0 flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
              <span className="text-sm font-medium text-slate-800">
                {formatFieldName(row.field)}
              </span>
              <span
                className="text-sm font-medium text-slate-600"
                dir="rtl"
                lang="ar"
              >
                {visionPocFieldLabelArabic(row.field)}
              </span>
            </div>
          ) : (
            <span className="text-sm font-medium text-slate-600">
              {formatFieldName(row.field)}
            </span>
          )}
          {isMatch && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
              <CheckCircle className="size-3" strokeWidth={1.5} />
              Verified
            </span>
          )}
          {isDifference && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
              <AlertTriangle className="size-3" strokeWidth={1.5} />
              Difference Found
            </span>
          )}
          {isPending &&
            (extractionOnly &&
            row.document_value != null &&
            String(row.document_value).trim() !== "" ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-800">
                Extracted
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                Needs Review
              </span>
            ))}
        </div>

        {/* 2-column: document | official record — or single column for Vision POC / EXTRACTED */}
        <div
          className={cn(
            "grid grid-cols-1 gap-4",
            !extractionOnly && "sm:grid-cols-2"
          )}
        >
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {extractionOnly ? "Extracted value" : "From Your Document"}
            </p>
            {extractionOnly && bilingualExtractedDisplay ? (
              <ExtractedValue field={row.field} value={row.document_value} />
            ) : (
              <p className="font-semibold text-slate-900">
                {formatValue(row.document_value)}
              </p>
            )}
          </div>
          {!extractionOnly && (
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-emerald-600" strokeWidth={2} aria-hidden />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {registryName}
                </span>
              </div>
              <p className="font-semibold text-slate-900">
                {formatValue(row.api_value)}
              </p>
              <p className="mt-1 text-[10px] text-slate-500" title="This data comes from official filings submitted by the organisation.">
                {sourceEmoji} {sourceBadge}
              </p>
              {syncedAt && (
                <p className="mt-0.5 text-[10px] text-slate-400">
                  Live sync: {formatLiveSyncTimestamp(syncedAt)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* "Why is this different?" — reduces anxiety when mismatch appears */}
        {isDifference && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowWhyDifferent(!showWhyDifferent);
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-700 hover:text-amber-800 hover:underline"
            >
              <HelpCircle className="size-3.5" strokeWidth={1.5} />
              Why is this different?
            </button>
            {showWhyDifferent && (
              <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                {WHY_DIFFERENT_EXPLANATION}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
