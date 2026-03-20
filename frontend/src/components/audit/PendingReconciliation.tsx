"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getHitlCheckpointsSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AlertTriangle, Loader2, ArrowRight } from "lucide-react";

export interface PendingReconciliationProps {
  className?: string;
}

/**
 * Phase 7.8: Pending Reconciliation card — Priority Discrepancies count;
 * Unassigned Reviewers (placeholder); Resolve Queues button.
 */
export function PendingReconciliation({ className }: PendingReconciliationProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["hitl-checkpoints-summary"],
    queryFn: () => getHitlCheckpointsSummary(),
  });

  if (error) {
    return (
      <div
        className={cn(
          "rounded-lg border border-border bg-muted/30 p-4",
          className
        )}
      >
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <AlertTriangle className="size-4" aria-hidden />
          Pending Reconciliation
        </h2>
        <p className="mt-1 text-sm text-destructive">Failed to load summary</p>
      </div>
    );
  }

  const priorityCount = data?.total ?? 0;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-muted/30 p-4 flex flex-col",
        className
      )}
    >
      <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
        <AlertTriangle className="size-4" aria-hidden />
        Pending Reconciliation
      </h2>
      <div className="mt-3 flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            Priority Discrepancies
          </span>
          {isLoading ? (
            <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            <span className="text-lg font-semibold tabular-nums text-foreground">
              {priorityCount}
            </span>
          )}
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            Unassigned Reviewers
          </span>
          <span className="text-sm tabular-nums text-muted-foreground">
            —
          </span>
        </div>
      </div>
      <div className="mt-4">
        <Link href="/hitl" aria-label="Go to verification queue to resolve discrepancies">
          <Button variant="outline" size="sm" className="w-full gap-1.5 sm:w-auto">
            Resolve Queues
            <ArrowRight className="size-3.5" aria-hidden />
          </Button>
        </Link>
      </div>
    </div>
  );
}
