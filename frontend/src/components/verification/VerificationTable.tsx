"use client";

import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, AlertTriangle, Clock, ShieldCheck } from "lucide-react";
import type { VerificationFieldRow } from "@/lib/api";
import { cn } from "@/lib/utils";

const columnHelper = createColumnHelper<VerificationFieldRow>();

const columns: ColumnDef<VerificationFieldRow, unknown>[] = [
  columnHelper.accessor("field", {
    header: "FIELD NAME",
    cell: ({ getValue }) => (
      <span className="font-medium text-[#0f172a]">
        {formatFieldName(String(getValue() ?? ""))}
      </span>
    ),
  }),
  columnHelper.accessor("document_value", {
    header: "FROM YOUR DOCUMENT",
    cell: ({ getValue }) => (
      <span className="font-mono text-sm text-[#0f172a]">
        {formatValue(getValue())}
      </span>
    ),
  }),
  columnHelper.accessor("api_value", {
    header: () => (
      <span className="inline-flex items-center gap-1.5">
        <ShieldCheck className="size-3.5 text-emerald-600" strokeWidth={2} aria-hidden />
        OFFICIAL RECORD
      </span>
    ),
    cell: ({ getValue }) => (
      <span className="font-mono text-sm text-[#0f172a]">
        {formatValue(getValue())}
      </span>
    ),
  }),
  columnHelper.accessor("status", {
    header: "STATUS",
    cell: ({ getValue }) => {
      const status = String(getValue() ?? "PENDING");
      if (status === "VERIFIED") {
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2 py-0.5 text-[#059669]">
            <CheckCircle className="size-3.5" strokeWidth={1.5} aria-hidden />
            <span className="text-xs font-medium">Verified</span>
          </span>
        );
      }
      if (status === "DISCREPANCY") {
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">
            <AlertTriangle className="size-3.5" strokeWidth={1.5} aria-hidden />
            <span className="text-xs font-medium">Difference Found</span>
          </span>
        );
      }
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[#64748b]">
          <Clock className="size-3.5" strokeWidth={1.5} aria-hidden />
          <span className="text-xs font-medium">Needs Review</span>
        </span>
      );
    },
  }),
];

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

function rowStatusClass(status: string): string {
  const base = "transition-colors";
  switch (status) {
    case "VERIFIED":
      return `${base} hover:bg-[#f0fdf4]/50`;
    case "DISCREPANCY":
      return `${base} bg-[#fff1f2] hover:bg-[#ffe4e6]`;
    case "PENDING":
    default:
      return `${base} hover:bg-[#f8fafc]`;
  }
}

export interface VerificationTableProps {
  rows: VerificationFieldRow[];
  isLoading?: boolean;
  error?: string | null;
  className?: string;
  onDiscrepancyRowClick?: (row: VerificationFieldRow) => void;
}

export function VerificationTable({
  rows,
  isLoading = false,
  error = null,
  className,
  onDiscrepancyRowClick,
}: VerificationTableProps) {
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (error) {
    return (
      <div
        className={cn(
          "flex flex-1 items-center justify-center p-8 text-[#dc2626]",
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
            <TableRow className="border-[#e2e8f0] hover:bg-transparent">
              <TableHead className="h-9 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Field Name
              </TableHead>
              <TableHead className="h-9 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                From Your Document
              </TableHead>
              <TableHead className="h-9 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Official Record
              </TableHead>
              <TableHead className="h-9 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Status
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 6 }).map((_, i) => (
              <TableRow key={i} className="border-[#e2e8f0]">
                <TableCell className="px-3 py-2">
                  <Skeleton className="h-4 w-28" />
                </TableCell>
                <TableCell className="px-3 py-2">
                  <Skeleton className="h-4 w-36" />
                </TableCell>
                <TableCell className="px-3 py-2">
                  <Skeleton className="h-4 w-32" />
                </TableCell>
                <TableCell className="px-3 py-2">
                  <Skeleton className="h-5 w-20 rounded-full" />
                </TableCell>
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
        <p className="text-sm text-[#64748b]">No verification data available</p>
      </div>
    );
  }

  return (
    <div className={cn("overflow-auto", className)}>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow
              key={headerGroup.id}
              className="border-[#e2e8f0] hover:bg-transparent"
            >
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className="h-9 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[#64748b]"
                >
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
          {table.getRowModel().rows.map((row) => {
            const isDiscrepancy = row.original.status === "DISCREPANCY";
            const isClickable = isDiscrepancy && onDiscrepancyRowClick;
            const fieldName = formatFieldName(row.original.field);
            return (
              <TableRow
                key={row.id}
                className={cn(
                  "border-[#e2e8f0]",
                  rowStatusClass(row.original.status),
                  isClickable && "cursor-pointer"
                )}
                onClick={
                  isClickable
                    ? () => onDiscrepancyRowClick(row.original)
                    : undefined
                }
                aria-label={
                  isClickable
                    ? `Difference found: ${fieldName}. Click to resolve.`
                    : undefined
                }
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className="px-3 py-2"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
