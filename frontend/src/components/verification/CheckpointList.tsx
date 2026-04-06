"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
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
import {
  getHitlCheckpoints,
  listDocuments,
  type CheckpointListItem,
} from "@/lib/api";
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
  { value: "financial", label: "Financial" },
  { value: "vision_poc", label: "Vision POC" },
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

  /** Vision POC / EXTRACTED paths finish as COMPLETED — they never appear in the HITL queue */
  const { data: completedDocs, isLoading: completedLoading } = useQuery({
    queryKey: ["documents-completed-sidebar", auditTarget],
    queryFn: () =>
      listDocuments({
        status_filter: "COMPLETED",
        audit_target: auditTarget === ALL ? undefined : auditTarget,
        limit: 20,
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
        <p className="mt-1 text-xs leading-snug text-muted-foreground">
          Only items <strong className="font-medium">pending human review</strong> appear
          here. Successful Vision POC runs are{" "}
          <strong className="font-medium">completed</strong> without a review step — see
          below.
        </p>
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
            No documents awaiting human review for this filter.
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

      {/* Completed uploads (e.g. Vision POC) — same verification viewer, different queue */}
      <div className="shrink-0 border-t border-border px-3 py-2">
        <span className="text-sm font-medium text-muted-foreground">
          Completed extractions
        </span>
        <p className="mt-1 text-xs text-muted-foreground">
          Open to see PDF + extracted fields.{" "}
          <Link href="/audit" className="font-medium text-foreground underline underline-offset-2">
            Audit Log
          </Link>{" "}
          has full history.
        </p>
      </div>
      <div className="max-h-48 min-h-0 overflow-auto border-t border-border">
        {completedLoading ? (
          <ul className="divide-y divide-border p-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <li key={i} className="px-3 py-2">
                <Skeleton className="h-4 w-full" />
              </li>
            ))}
          </ul>
        ) : !completedDocs?.length ? (
          <p className="p-4 text-sm text-muted-foreground">
            No completed documents for this filter yet.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {completedDocs.map((doc) => (
              <li key={doc.id}>
                <Link
                  href={`/hitl?document_id=${doc.id}`}
                  className={cn(
                    "flex flex-col gap-0.5 px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/50",
                    selectedId === String(doc.id) && "bg-muted"
                  )}
                >
                  <span className="truncate font-medium text-foreground">
                    {doc.filename}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {doc.audit_target ?? "—"} · COMPLETED
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
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
