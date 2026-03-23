"use client";

import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getAuditLogs } from "@/lib/api";
import { FileDown } from "lucide-react";
import { AuditLogTable } from "@/components/audit/AuditLogTable";
import { AuditHealthIndex } from "@/components/audit/AuditHealthIndex";
import { PendingReconciliation } from "@/components/audit/PendingReconciliation";

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;
const DEFAULT_PAGE_SIZE = 20;
const STATUS_ALL = "__all__";
const DATE_RANGE_ALL = "__all__";

/** Task 7.3: Status filter options */
const STATUS_OPTIONS = [
  { value: STATUS_ALL, label: "All Entries" },
  { value: "VERIFIED", label: "Verified" },
  { value: "DISCREPANCY_FLAG", label: "Discrepancy" },
  { value: "PENDING_HUMAN_REVIEW", label: "Pending Review" },
];

/** Task 7.4: Date range preset options */
const DATE_RANGE_OPTIONS = [
  { value: DATE_RANGE_ALL, label: "All time" },
  { value: "7", label: "Last 7 Days" },
  { value: "30", label: "Last 30 Days" },
  { value: "90", label: "Last 90 Days" },
  { value: "custom", label: "Custom Range" },
];

function toYYYYMMDD(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/**
 * Phase 7.1–7.6: Audit Log page — status, date range, search, pagination, cards placeholder, AuditLogTable.
 */
const SEARCH_DEBOUNCE_MS = 300;

function AuditLogContent() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [status, setStatus] = useState<string>(STATUS_ALL);
  const [dateRangePreset, setDateRangePreset] = useState<string>(DATE_RANGE_ALL);
  const [customDateFrom, setCustomDateFrom] = useState<string>("");
  const [customDateTo, setCustomDateTo] = useState<string>("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { date_from, date_to } = useMemo(() => {
    if (dateRangePreset === DATE_RANGE_ALL) return { date_from: undefined, date_to: undefined };
    if (dateRangePreset === "custom") {
      const from = customDateFrom?.trim() || undefined;
      const to = customDateTo?.trim() || undefined;
      return { date_from: from, date_to: to };
    }
    const days = parseInt(dateRangePreset, 10);
    if (Number.isNaN(days) || days < 1) return { date_from: undefined, date_to: undefined };
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return { date_from: toYYYYMMDD(start), date_to: toYYYYMMDD(end) };
  }, [dateRangePreset, customDateFrom, customDateTo]);

  const { data, isLoading, error } = useQuery({
    queryKey: [
      "audit-logs",
      status === STATUS_ALL ? null : status,
      date_from ?? null,
      date_to ?? null,
      search || null,
      page,
      pageSize,
    ],
    queryFn: () =>
      getAuditLogs({
        page,
        page_size: pageSize,
        status: status === STATUS_ALL ? undefined : status,
        date_from: date_from ?? undefined,
        date_to: date_to ?? undefined,
        search: search || undefined,
      }),
  });

  const total = data?.total ?? 0;
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 0;
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = total === 0 ? 0 : Math.min(page * pageSize, total);

  const handleExportReport = () => {
    const items = data?.items ?? [];
    const report = {
      exported_at: new Date().toISOString(),
      page,
      page_size: pageSize,
      total,
      items,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-report-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col p-4 sm:p-6">
      {/* Page header */}
      <div className="mb-4 shrink-0">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Audit Log
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          System-wide verification records — filter by status, date range, and search
        </p>
      </div>

      {/* Filters row: Task 7.3 status; 7.4 date range; 7.5 search */}
      <div className="mb-4 flex flex-wrap items-end gap-4 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <div className="space-y-1.5">
          <label htmlFor="audit-status" className="block text-xs font-medium text-muted-foreground">
            Status
          </label>
          <Select
            value={status}
            onValueChange={(v) => {
              setStatus(v);
              setPage(1);
            }}
          >
            <SelectTrigger id="audit-status" className="w-full min-w-[140px] sm:w-[180px]">
              <SelectValue placeholder="All Entries" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="audit-date-range" className="block text-xs font-medium text-muted-foreground">
            Date range
          </label>
          <Select
            value={dateRangePreset}
            onValueChange={(v) => {
              setDateRangePreset(v);
              setPage(1);
            }}
          >
            <SelectTrigger id="audit-date-range" className="w-full min-w-[140px] sm:w-[160px]">
              <SelectValue placeholder="All time" />
            </SelectTrigger>
            <SelectContent>
              {DATE_RANGE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {dateRangePreset === "custom" && (
          <>
            <div className="space-y-1.5">
              <label htmlFor="audit-date-from" className="block text-xs font-medium text-muted-foreground">
                From
              </label>
              <Input
                id="audit-date-from"
                type="date"
                value={customDateFrom}
                onChange={(e) => {
                  setCustomDateFrom(e.target.value);
                  setPage(1);
                }}
                className="w-[140px]"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="audit-date-to" className="block text-xs font-medium text-muted-foreground">
                To
              </label>
              <Input
                id="audit-date-to"
                type="date"
                value={customDateTo}
                onChange={(e) => {
                  setCustomDateTo(e.target.value);
                  setPage(1);
                }}
                className="w-[140px]"
              />
            </div>
          </>
        )}
        <div className="flex-1 min-w-0 w-full sm:min-w-[200px] sm:max-w-[280px] space-y-1.5">
          <label htmlFor="audit-search" className="block text-xs font-medium text-muted-foreground">
            Search
          </label>
          <Input
            id="audit-search"
            type="search"
            placeholder="Search audit trails…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full"
            aria-label="Search audit trails"
          />
        </div>
      </div>

      {/* Cards row: Task 7.7 AuditHealthIndex; Task 7.8 PendingReconciliation */}
      <div className="mb-4 grid shrink-0 gap-4 sm:grid-cols-2">
        <AuditHealthIndex dateFrom={date_from} dateTo={date_to} />
        <PendingReconciliation />
      </div>

      {/* Table area (Task 7.2, 7.6, 7.9): AuditLogTable + Export + pagination */}
      <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-muted/30 flex flex-col">
        <div className="flex h-10 shrink-0 items-center justify-between gap-2 border-b border-border px-4">
          <span className="text-sm font-medium text-muted-foreground">
            Audit trails
          </span>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportReport}
              disabled={!data?.items?.length}
              className="gap-1.5 h-8"
              aria-label="Export audit report as JSON"
            >
              <FileDown className="size-3.5" aria-hidden />
              Export Report
            </Button>
            {data != null && total > 0 && (
              <span className="text-xs text-muted-foreground">
                Showing {startItem}–{endItem} of {total}
              </span>
            )}
            <div className="flex items-center gap-1.5">
              <label htmlFor="audit-page-size" className="text-xs text-muted-foreground whitespace-nowrap">
                Per page
              </label>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v));
                  setPage(1);
                }}
              >
                <SelectTrigger id="audit-page-size" className="h-8 w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-2">
          <AuditLogTable
            rows={data?.items ?? []}
            isLoading={isLoading}
            error={
              error
                ? error instanceof Error
                  ? error.message
                  : "Failed to load audit log"
                : null
            }
          />
        </div>
        {totalPages > 1 && data != null && (
          <div className="flex shrink-0 items-center justify-center gap-2 border-t border-border px-4 py-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded border border-border bg-background px-2 py-1 text-sm disabled:opacity-50"
              aria-label="Previous page"
            >
              Previous
            </button>
            <span className="text-sm text-muted-foreground" aria-live="polite">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded border border-border bg-background px-2 py-1 text-sm disabled:opacity-50"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuditLogPage() {
  return <AuditLogContent />;
}
