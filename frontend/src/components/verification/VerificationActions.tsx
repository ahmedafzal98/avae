"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  FileDown,
  CheckCircle,
  RotateCcw,
  Flag,
  Loader2,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentVerificationResponse } from "@/lib/api";
import {
  hitlOverride,
  hitlRequestClientRemediation,
  requeueDocument,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export interface VerificationActionsProps {
  documentId: number | string;
  verification: DocumentVerificationResponse | null | undefined;
  onSuccess?: () => void;
  onError?: (message: string) => void;
  className?: string;
}

/** Task 5.7: Export Report, Approve Entry, Re-run Extraction, Flag for Manual Review */
export function VerificationActions({
  documentId,
  verification,
  onSuccess,
  onError,
  className,
}: VerificationActionsProps) {
  const [loading, setLoading] = useState<"approve" | "requeue" | "flag" | null>(
    null
  );
  const [flagDialogOpen, setFlagDialogOpen] = useState(false);

  const checkpointId = String(documentId);
  // Approve/Flag apply to documents in PENDING_HUMAN_REVIEW (backend validates)
  const hasVerificationData = Boolean(verification?.rows?.length);

  const handleExport = () => {
    if (!verification) return;
    const blob = new Blob([JSON.stringify(verification, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `verification-report-${documentId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleApprove = async () => {
    setLoading("approve");
    try {
      await hitlOverride(checkpointId);
      onSuccess?.();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setLoading(null);
    }
  };

  const handleRequeue = async () => {
    setLoading("requeue");
    try {
      await requeueDocument(documentId);
      onSuccess?.();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Re-run failed");
    } finally {
      setLoading(null);
    }
  };

  const handleFlagConfirm = async () => {
    setLoading("flag");
    try {
      await hitlRequestClientRemediation(checkpointId);
      setFlagDialogOpen(false);
      onSuccess?.();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Flag failed");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <Button
        variant="outline"
        size="sm"
        onClick={handleExport}
        disabled={!verification}
        className="gap-1.5"
        aria-label="Export verification report"
      >
        <FileDown className="size-3.5" aria-hidden />
        Export Report
      </Button>

      <Button
        variant="default"
        size="sm"
        onClick={handleApprove}
        disabled={!hasVerificationData || loading !== null}
        className="gap-1.5 bg-tertiary hover:bg-tertiary/90 text-white"
        aria-label="Approve this entry"
      >
        {loading === "approve" ? (
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
        ) : (
          <CheckCircle className="size-3.5" aria-hidden />
        )}
        Approve Entry
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={handleRequeue}
        disabled={loading !== null}
        className="gap-1.5"
      >
        {loading === "requeue" ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <RotateCcw className="size-3.5" />
        )}
        Re-run Extraction
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={() => setFlagDialogOpen(true)}
        disabled={!hasVerificationData || loading !== null}
        className="gap-1.5"
      >
        {loading === "flag" ? (
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
        ) : (
          <Flag className="size-3.5" aria-hidden />
        )}
        Flag for Manual Review
      </Button>

      <Dialog open={flagDialogOpen} onOpenChange={setFlagDialogOpen}>
        <DialogContent>
          <div className="relative grid gap-4">
            {loading === "flag" && (
              <div
                className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-background/80"
                aria-live="polite"
                aria-label="Flagging for review"
              >
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
            )}
          <DialogHeader>
            <DialogTitle>Flag for Manual Review</DialogTitle>
            <DialogDescription>
              This will mark the document as requiring client remediation. The
              client will be notified to upload a corrected document. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setFlagDialogOpen(false)}
              disabled={loading !== null}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleFlagConfirm}
              disabled={loading !== null}
              className="gap-1.5"
              aria-label="Confirm flag for manual review"
            >
              {loading === "flag" ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
              ) : (
                <Flag className="size-3.5" aria-hidden />
              )}
              Flag for Review
            </Button>
          </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
