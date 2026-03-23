"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
} from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/verification/StatusBadge";
import {
  getAuditLogDetails,
  type AuditLogListItem,
  type AuditLogDetailResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { ExternalLink, ChevronDown, ChevronRight } from "lucide-react";

const columnHelper = createColumnHelper<AuditLogListItem>();

function formatTimestamp(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function formatAuditTarget(target: string): string {
  if (target === "companies_house") return "Companies House";
  if (target === "hm_land_registry") return "Land Registry";
  if (target === "epc") return "EPC";
  if (target === "financial") return "Financial";
  return target;
}

function formatFieldName(key: string): string {
  return key
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

function formatCellValue(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "string") return val;
  if (typeof val === "number" || typeof val === "boolean") return String(val);
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

function DataSummaryTable({
  data,
  title,
  className,
}: {
  data: Record<string, unknown>;
  title: string;
  className?: string;
}) {
  const entries = Object.entries(data ?? {}).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );
  if (entries.length === 0) return null;
  return (
    <div className={className}>
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        {title}
      </p>
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <tbody>
            {entries.map(([key, val]) => (
              <tr key={key} className="border-b border-border last:border-b-0">
                <td className="px-3 py-2 text-muted-foreground font-medium w-1/3">
                  {formatFieldName(key)}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {formatCellValue(val)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DiscrepancySummary({
  flags,
  className,
}: {
  flags: Array<{ field?: string; extracted?: unknown; api?: unknown }>;
  className?: string;
}) {
  const valid = flags?.filter((f) => f && typeof f === "object" && (f.field ?? f.extracted ?? f.api) != null) ?? [];
  if (valid.length === 0) return null;
  return (
    <div className={className}>
      <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 mb-2">
        Difference Found — {valid.length} field{valid.length !== 1 ? "s" : ""}
      </p>
      <div className="rounded-lg border border-amber-200 overflow-hidden bg-amber-50/30">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-amber-50/50 border-b border-amber-200">
              <th className="px-3 py-2 text-left text-xs font-semibold text-amber-800">Field</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-amber-800">From Your Document</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-amber-800">Official Record</th>
            </tr>
          </thead>
          <tbody>
            {valid.map((f, i) => (
              <tr key={i} className="border-b border-amber-100 last:border-b-0">
                <td className="px-3 py-2 font-medium text-amber-900">
                  {formatFieldName(f.field ?? "")}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{formatCellValue(f.extracted)}</td>
                <td className="px-3 py-2 font-mono text-xs">{formatCellValue(f.api)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Full audit details in expandable row — human-readable, no raw JSON (Phase 7.9) */
function AuditLogDetailPanel({ detail }: { detail: AuditLogDetailResponse }) {
  const extracted = (detail.extracted_json ?? {}) as Record<string, unknown>;
  const apiRaw = detail.api_response_json;
  // EPC API may return array; use first row
  const official = (Array.isArray(apiRaw) && apiRaw[0] != null
    ? apiRaw[0]
    : apiRaw ?? {}
  ) as Record<string, unknown>;
  const flags = (detail.discrepancy_flags ?? []) as Array<{
    field?: string;
    extracted?: unknown;
    api?: unknown;
  }>;

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Document
        </p>
        <p className="font-mono text-sm break-all">{detail.filename || "—"}</p>
      </div>

      {flags.length > 0 && (
        <DiscrepancySummary flags={flags} />
      )}

      <DataSummaryTable
        data={extracted}
        title="From Your Document"
      />

      {official != null && Object.keys(official).length > 0 && (
        <DataSummaryTable
          data={official}
          title="Official Record"
        />
      )}
    </div>
  );
}

function makeColumns(
  expandedId: number | null,
  onToggleExpand: (id: number) => void
): ColumnDef<AuditLogListItem, unknown>[] {
  return [
  {
    id: "expand",
    header: "",
    cell: ({ row }) => {
      const id = row.original.id;
      const isExpanded = expandedId === id;
      return (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleExpand(id);
          }}
          className="p-1 rounded hover:bg-muted"
          aria-label={isExpanded ? "Collapse row" : "Expand row"}
        >
          {isExpanded ? (
            <ChevronDown className="size-4 text-muted-foreground" aria-hidden />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
          )}
        </button>
      );
    },
  },
  columnHelper.accessor("created_at", {
    header: "Date / Time",
    cell: ({ getValue }) => (
      <span className="text-muted-foreground text-sm whitespace-nowrap">
        {formatTimestamp(String(getValue() ?? ""))}
      </span>
    ),
  }),
  columnHelper.accessor("document_id", {
    header: "Document ID",
    cell: ({ getValue }) => (
      <span className="font-mono text-sm">{getValue() ?? "—"}</span>
    ),
  }),
  columnHelper.accessor("audit_target", {
    header: "Audit Target",
    cell: ({ getValue }) => (
      <span className="text-sm">{formatAuditTarget(String(getValue() ?? ""))}</span>
    ),
  }),
  columnHelper.accessor("verification_status", {
    header: "Verification Status",
    cell: ({ getValue }) => {
      const status = String(getValue() ?? "PENDING");
      return <StatusBadge status={status} showIcon={true} />;
    },
  }),
  columnHelper.display({
    id: "actions",
    header: "Actions",
    cell: ({ row }) => (
      <Link href={`/hitl?document_id=${row.original.document_id}`}>
        <Button variant="ghost" size="sm" className="gap-1.5 h-8">
          <ExternalLink className="size-3.5" aria-hidden />
          View
        </Button>
      </Link>
    ),
  }),
];
}

export interface AuditLogTableProps {
  rows: AuditLogListItem[];
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}

/**
 * Phase 7.2, 7.9: Audit log table — expand row for full details; Date/Timestamp, Document ID, Audit Target, Status, Actions.
 */
export function AuditLogTable({
  rows,
  isLoading = false,
  error = null,
  className,
}: AuditLogTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ["audit-log-detail", expandedId],
    queryFn: () => getAuditLogDetails(expandedId!),
    enabled: expandedId != null,
  });

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const columns = makeColumns(expandedId, toggleExpand);
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table API
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (error) {
    return (
      <div
        className={cn(
          "flex flex-1 items-center justify-center p-8 text-destructive",
          className
        )}
      >
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={cn("overflow-auto", className)}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10" />
              <TableHead>Date</TableHead>
              <TableHead>Document ID</TableHead>
              <TableHead>Audit Target</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-16" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 8 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
                <TableCell><Skeleton className="h-4 w-8" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-1 items-center justify-center p-8",
          className
        )}
      >
        <p className="text-sm text-muted-foreground">No audit log entries</p>
      </div>
    );
  }

  return (
    <div className={cn("overflow-auto", className)}>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext()
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <React.Fragment key={row.id}>
              <TableRow>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
              {expandedId === row.original.id && (
                <TableRow key={`${row.id}-detail`} className="bg-muted/30">
                  <TableCell colSpan={columns.length} className="p-4">
                    {detailLoading ? (
                      <div className="space-y-3">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-20 w-full" />
                        <Skeleton className="h-24 w-full" />
                      </div>
                    ) : detailData ? (
                      <AuditLogDetailPanel detail={detailData} />
                    ) : null}
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
