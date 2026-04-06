"use client";

import Link from "next/link";
import { Eye, MoreHorizontal } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useQuery } from "@tanstack/react-query";
import { getHitlCheckpoints, type CheckpointListItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

function formatAuditTarget(auditTarget: string): string {
  const map: Record<string, string> = {
    companies_house: "Companies House",
    epc: "EPC",
    hm_land_registry: "Land Registry",
    financial: "Financial",
    vision_poc: "Vision POC",
  };
  return map[auditTarget] ?? auditTarget;
}

function StatusPill({ status }: { status: string }) {
  const isPending = status === "PENDING_HUMAN_REVIEW";
  const isAwaiting = status === "AWAITING_CLIENT_REMEDIATION";
  const styles = isPending
    ? "bg-[#d97706]/15 text-[#b45309]"
    : isAwaiting
      ? "bg-[#6366f1]/15 text-[#4f46e5]"
      : "bg-[#64748b]/15 text-[#475569]";
  const labels: Record<string, string> = {
    PENDING_HUMAN_REVIEW: "Pending Review",
    AWAITING_CLIENT_REMEDIATION: "Awaiting Client",
  };
  const label = labels[status] ?? status;
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        styles
      )}
    >
      {label}
    </span>
  );
}

function UrgencyDots({ count }: { count: number }) {
  const level = Math.min(5, Math.max(1, Math.ceil(count / 2) + 1));
  return (
    <div className="flex gap-0.5" role="img" aria-label={`${count} discrepancies`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "size-1.5 rounded-full",
            i < level ? "bg-[#0f172a]" : "bg-[#f1f5f9]"
          )}
        />
      ))}
    </div>
  );
}

export function VerificationQueueTable() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-hitl-checkpoints"],
    queryFn: () =>
      getHitlCheckpoints({ page: 1, page_size: 10 }),
  });

  const checkpoints = data?.checkpoints ?? [];

  return (
    <div className="overflow-hidden rounded-lg border border-[#e2e8f0] bg-white p-6">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
        Active Verification Queue
      </p>
      {isLoading ? (
        <div className="mt-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="mt-4 text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load queue"}
        </p>
      ) : checkpoints.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No documents awaiting review. Upload a document to get started.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-[#e2e8f0] hover:bg-transparent">
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Document ID
              </TableHead>
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Filename
              </TableHead>
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Type
              </TableHead>
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Discrepancies
              </TableHead>
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Status
              </TableHead>
              <TableHead className="h-10 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[#64748b]">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {checkpoints.map((item: CheckpointListItem) => {
              const flagCount = item.discrepancy_flags?.length ?? 0;
              return (
                <TableRow
                  key={item.checkpoint_id}
                  className="border-[#e2e8f0] hover:bg-[#f8fafc]"
                >
                  <TableCell className="px-4 py-3 font-mono text-sm text-[#0f172a]">
                    {item.checkpoint_id}
                  </TableCell>
                  <TableCell className="px-4 py-3 text-sm font-semibold text-[#0f172a]">
                    {item.filename}
                  </TableCell>
                  <TableCell className="px-4 py-3 text-sm text-[#64748b]">
                    {formatAuditTarget(item.audit_target)}
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <UrgencyDots count={flagCount} />
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <StatusPill status={item.status} />
                  </TableCell>
                  <TableCell className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        asChild
                        className="text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus-visible:ring-2 focus-visible:ring-[#475569] focus-visible:ring-offset-0"
                      >
                        <Link
                          href={`/hitl?document_id=${item.checkpoint_id}`}
                          aria-label={`View ${item.checkpoint_id}`}
                        >
                          <Eye className="size-4" strokeWidth={1.5} />
                        </Link>
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus-visible:ring-2 focus-visible:ring-[#475569] focus-visible:ring-offset-0"
                            aria-label="More actions"
                          >
                            <MoreHorizontal className="size-4" strokeWidth={1.5} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="border-[#e2e8f0]">
                          <DropdownMenuItem asChild>
                            <Link href={`/hitl?document_id=${item.checkpoint_id}`}>
                              Review
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link href={`/audit?search=${item.checkpoint_id}`}>
                              View in Audit Log
                            </Link>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
