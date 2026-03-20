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

/** Full audit details in expandable row (Phase 7.9) */
function AuditLogDetailPanel({ detail }: { detail: AuditLogDetailResponse }) {
  return (
    <div className="grid gap-3 text-sm">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <span className="font-medium text-muted-foreground">Filename</span>
          <p className="font-mono text-xs break-all">{detail.filename || "—"}</p>
        </div>
      </div>
      {detail.discrepancy_flags && detail.discrepancy_flags.length > 0 && (
        <div>
          <span className="font-medium text-muted-foreground">Discrepancy flags</span>
          <pre className="mt-1 max-h-32 overflow-auto rounded border border-border bg-background p-2 text-xs">
            {JSON.stringify(detail.discrepancy_flags, null, 2)}
          </pre>
        </div>
      )}
      <div>
        <span className="font-medium text-muted-foreground">Extracted JSON</span>
        <pre className="mt-1 max-h-40 overflow-auto rounded border border-border bg-background p-2 text-xs">
          {JSON.stringify(detail.extracted_json, null, 2)}
        </pre>
      </div>
      {detail.api_response_json != null && Object.keys(detail.api_response_json).length > 0 && (
        <div>
          <span className="font-medium text-muted-foreground">API response</span>
          <pre className="mt-1 max-h-40 overflow-auto rounded border border-border bg-background p-2 text-xs">
            {JSON.stringify(detail.api_response_json, null, 2)}
          </pre>
        </div>
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
