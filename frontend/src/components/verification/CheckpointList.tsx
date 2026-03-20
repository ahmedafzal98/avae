"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/verification/StatusBadge";
import { getHitlCheckpoints, type CheckpointListItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";

const PAGE_SIZE = 10;
const ALL = "__all__";
const STATUS_OPTIONS = [
  { value: ALL, label: "All statuses" },
  { value: "PENDING_HUMAN_REVIEW", label: "Pending Review" },
  { value: "AWAITING_CLIENT_REMEDIATION", label: "Awaiting Client" },
];
const AUDIT_TARGET_OPTIONS = [
  { value: ALL, label: "All targets" },
  { value: "epc", label: "EPC" },
  { value: "companies_house", label: "Companies House" },
  { value: "hm_land_registry", label: "Land Registry" },
];

export interface CheckpointListProps {
  className?: string;
}

/** Task 5.8: Checkpoint list with filters and pagination */
export function CheckpointList({ className }: CheckpointListProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("document_id");

  const [status, setStatus] = useState<string>(ALL);
  const [auditTarget, setAuditTarget] = useState<string>(ALL);
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: [
      "hitl-checkpoints",
      status === ALL ? undefined : status,
      auditTarget === ALL ? undefined : auditTarget,
      page,
    ],
    queryFn: () =>
      getHitlCheckpoints({
        status: status === ALL ? undefined : status,
        audit_target: auditTarget === ALL ? undefined : auditTarget,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const selectCheckpoint = useCallback(
    (checkpointId: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("document_id", checkpointId);
      router.push(`/hitl?${params.toString()}`);
    },
    [router, searchParams]
  );

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 0;

  return (
    <div
      className={cn(
        "flex w-full flex-col overflow-hidden rounded-lg border border-border bg-muted/30",
        "max-h-[40vh] lg:max-h-none lg:w-72 lg:shrink-0",
        className
      )}
    >
      <div className="shrink-0 border-b border-border px-3 py-2">
        <span className="text-sm font-medium text-muted-foreground">
          Documents for Review
        </span>
      </div>

      {/* Filters */}
      <div className="shrink-0 space-y-2 border-b border-border p-3">
        <div>
          <label className="mb-1 block text-xs text-muted-foreground">
            Status
          </label>
          <Select
            value={status}
            onValueChange={(v) => {
              setStatus(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 w-full">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted-foreground">
            Audit Target
          </label>
          <Select
            value={auditTarget}
            onValueChange={(v) => {
              setAuditTarget(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 w-full">
              <SelectValue placeholder="All targets" />
            </SelectTrigger>
            <SelectContent>
              {AUDIT_TARGET_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* List */}
      <div className="min-h-0 flex-1 overflow-auto">
        {isLoading ? (
          <ul className="divide-y divide-border p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <li key={i} className="flex items-start gap-2 px-3 py-2.5">
                <Skeleton className="mt-0.5 size-4 shrink-0 rounded" />
                <div className="min-w-0 flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              </li>
            ))}
          </ul>
        ) : error ? (
          <div className="p-4 text-sm text-destructive">
            {error instanceof Error ? error.message : "Failed to load checkpoints"}
          </div>
        ) : !data?.checkpoints?.length ? (
          <div className="p-4 text-sm text-muted-foreground">
            No documents awaiting review
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {data.checkpoints.map((cp) => (
              <CheckpointRow
                key={cp.checkpoint_id}
                checkpoint={cp}
                isSelected={selectedId === cp.checkpoint_id}
                onSelect={() => selectCheckpoint(cp.checkpoint_id)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > PAGE_SIZE && (
        <div className="flex shrink-0 items-center justify-between border-t border-border px-3 py-2">
          <span className="text-xs text-muted-foreground">
            {data.total} total
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span className="text-xs tabular-nums">
              {page} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function CheckpointRow({
  checkpoint,
  isSelected,
  onSelect,
}: {
  checkpoint: CheckpointListItem;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const flagCount = checkpoint.discrepancy_flags?.length ?? 0;

  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "flex w-full flex-col gap-1 px-3 py-2.5 text-left transition-colors hover:bg-muted/50",
          isSelected && "bg-muted"
        )}
      >
        <div className="flex items-start gap-2">
          <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">
              {checkpoint.filename}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <StatusBadge status={checkpoint.status} showIcon={false} />
              {flagCount > 0 && (
                <span className="text-xs text-destructive">
                  {flagCount} discrepancy{flagCount !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
        </div>
      </button>
    </li>
  );
}
