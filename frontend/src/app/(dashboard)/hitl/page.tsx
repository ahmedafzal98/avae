"use client";

import dynamic from "next/dynamic";
import { Suspense, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getDocumentPdfUrl,
  getDocumentVerification,
  hitlOverride,
  hitlRequestClientRemediation,
  requeueDocument,
} from "@/lib/api";
import type { VerificationFieldRow } from "@/lib/api";
import { DocumentViewerPane } from "@/components/verification/DocumentViewerPane";
import { VerificationFeedPane } from "@/components/verification/VerificationFeedPane";
import { CheckpointList } from "@/components/verification/CheckpointList";
import { HITLModal } from "@/components/verification/HITLModal";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toastError } from "@/lib/toast";
import { X, Loader2 } from "lucide-react";

/**
 * DocumentPreview: lazy-loaded with ssr: false (Plan §11.1) — heavy PDF lib
 * must not block initial page load.
 */
const DocumentPreview = dynamic(
  () =>
    import("@/components/verification/DocumentPreview").then(
      (m) => m.DocumentPreview
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">Loading PDF viewer…</p>
      </div>
    ),
  }
);

/**
 * Verification Dashboard (Phase 5, Tasks 5.1, 5.3, 5.8, 5.9)
 *
 * Layout: Checkpoint list (left) | 50/50 split: PDF viewer | Verification table
 * Responsive: stacked on small screens (Task 5.9).
 */
function VerificationDashboardContent() {
  const searchParams = useSearchParams();
  const documentId = searchParams.get("document_id");
  const documentIdNum = useMemo(() => {
    if (!documentId) return null;
    const id = parseInt(documentId, 10);
    return Number.isNaN(id) ? null : id;
  }, [documentId]);

  const pdfUrl = useMemo(() => {
    if (!documentIdNum) return null;
    return getDocumentPdfUrl(documentIdNum);
  }, [documentIdNum]);

  const {
    data: verification,
    isLoading: verificationLoading,
    error: verificationError,
    refetch: refetchVerification,
  } = useQuery({
    queryKey: ["document-verification", documentIdNum],
    queryFn: () => getDocumentVerification(documentIdNum!),
    enabled: documentIdNum != null,
  });

  const [hitlModalOpen, setHitlModalOpen] = useState(false);
  const [hitlSelectedRow, setHitlSelectedRow] = useState<VerificationFieldRow | null>(null);
  const [hitlError, setHitlError] = useState<string | null>(null);
  const [hitlOverrideJustificationPrefill, setHitlOverrideJustificationPrefill] = useState<string | null>(null);
  const [flagDialogOpen, setFlagDialogOpen] = useState(false);
  const [flagLoading, setFlagLoading] = useState(false);
  /** Row hovered/clicked for PDF highlight (red=discrepancy, green=verified) */
  const [highlightedRow, setHighlightedRow] = useState<VerificationFieldRow | null>(null);

  const closeHitlModal = useCallback(() => {
    setHitlModalOpen(false);
    setHitlSelectedRow(null);
    setHitlOverrideJustificationPrefill(null);
  }, []);

  const openHitlModal = useCallback(
    (row?: VerificationFieldRow | null, prefillJustification?: string | null) => {
      const isSameRow =
        hitlSelectedRow &&
        row &&
        hitlSelectedRow.field === row.field &&
        String(hitlSelectedRow.document_value) === String(row.document_value);
      if (hitlModalOpen && isSameRow) {
        closeHitlModal();
        return;
      }
      setHitlSelectedRow(row ?? null);
      setHitlOverrideJustificationPrefill(prefillJustification ?? null);
      setHitlModalOpen(true);
    },
    [hitlModalOpen, hitlSelectedRow, closeHitlModal]
  );

  const handleHitlModalOpenChange = useCallback(
    (next: boolean) => {
      setHitlModalOpen(next);
      if (!next) {
        setHitlSelectedRow(null);
        setHitlOverrideJustificationPrefill(null);
      }
    },
    []
  );

  const clearHitlError = useCallback(() => setHitlError(null), []);

  const handleConfirmCorrect = useCallback(async () => {
    if (!documentIdNum) return;
    try {
      await hitlOverride(String(documentIdNum));
      refetchVerification();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Approve failed");
    }
  }, [documentIdNum, refetchVerification]);

  const handleFlagForReview = useCallback(() => setFlagDialogOpen(true), []);

  const handleFlagConfirm = useCallback(async () => {
    if (!documentIdNum) return;
    setFlagLoading(true);
    try {
      await hitlRequestClientRemediation(String(documentIdNum));
      setFlagDialogOpen(false);
      refetchVerification();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Flag failed");
    } finally {
      setFlagLoading(false);
    }
  }, [documentIdNum, refetchVerification]);

  const handleReExtract = useCallback(async () => {
    if (!documentIdNum) return;
    try {
      await requeueDocument(documentIdNum);
      refetchVerification();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Re-extract failed");
    }
  }, [documentIdNum, refetchVerification]);

  const hasDiscrepancies = (verification?.rows?.some((r) => r.status === "DISCREPANCY")) ?? false;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col p-6">
      {/* Page header */}
      <div className="mb-6 shrink-0 space-y-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Verification
          </h1>
          <p className="mt-1 text-sm text-[#64748b]">
            Review documents requiring human verification — compare submitted
            documents against official registry records
          </p>
        </div>
        {hitlError && (
          <div
            className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            role="alert"
          >
            <span className="flex-1">{hitlError}</span>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={clearHitlError}
              aria-label="Dismiss error"
            >
              <X className="size-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Layout: Checkpoint list | 50/50 PDF | Verification Summary — equal size, full height */}
      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
        <CheckpointList className="lg:shrink-0" />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {/* 50/50 split: Document Viewer | Verification Summary — equal width, full height */}
          <div className="flex min-h-0 min-w-0 flex-1 gap-4 lg:flex-row">
            {/* Left pane — PDF Viewer */}
            <div className="flex min-h-[400px] min-w-0 flex-1 flex-col lg:min-w-0">
              <DocumentViewerPane hasDocument={!!pdfUrl} className="h-full min-h-0">
                <div className="h-full min-h-0">
                  <DocumentPreview
                    fileUrl={pdfUrl}
                    highlightArea={
                      highlightedRow?.pdf_location
                        ? {
                            pageIndex: highlightedRow.pdf_location.page_index,
                            left: highlightedRow.pdf_location.left,
                            top: highlightedRow.pdf_location.top,
                            width: highlightedRow.pdf_location.width,
                            height: highlightedRow.pdf_location.height,
                          }
                        : null
                    }
                    highlightColor={
                      highlightedRow?.status === "DISCREPANCY" ? "red" : "green"
                    }
                  />
                </div>
              </DocumentViewerPane>
            </div>

            {/* Right pane — Verification Summary */}
            <div className="flex min-h-[400px] min-w-0 flex-1 flex-col lg:min-w-0">
              <VerificationFeedPane
                className="h-full min-h-0"
                batchId={documentIdNum != null ? `Document #${documentIdNum}` : undefined}
                auditTarget={verification?.audit_target}
                officialRecordSyncedAt={verification?.official_record_synced_at}
                rows={verification?.rows ?? []}
                isLoading={verificationLoading}
                error={
                  verificationError
                    ? verificationError instanceof Error
                      ? verificationError.message
                      : "Failed to load verification data"
                    : null
                }
                onConfirmCorrect={documentIdNum ? handleConfirmCorrect : undefined}
                onFlagForReview={documentIdNum ? handleFlagForReview : undefined}
                onReExtract={documentIdNum ? handleReExtract : undefined}
                onDiscrepancyCardClick={documentIdNum ? (row) => openHitlModal(row) : undefined}
                onRowHighlight={setHighlightedRow}
                highlightedRow={highlightedRow}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Flag for Review confirmation */}
      <Dialog open={flagDialogOpen} onOpenChange={setFlagDialogOpen}>
        <DialogContent>
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
              disabled={flagLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleFlagConfirm}
              disabled={flagLoading}
              className="gap-1.5"
            >
              {flagLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : null}
              Flag for Review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* HITL Modal (Task 6.1) */}
      {documentIdNum && (
        <HITLModal
          open={hitlModalOpen}
          onOpenChange={handleHitlModalOpenChange}
          checkpointId={String(documentIdNum)}
          verification={verification ?? undefined}
          selectedRow={hitlSelectedRow}
          initialOverrideJustification={hitlOverrideJustificationPrefill}
          onSuccess={() => {
            closeHitlModal();
            setHitlError(null);
            refetchVerification();
          }}
          onError={(msg) => {
            setHitlError(msg);
            toastError(msg);
          }}
        />
      )}
    </div>
  );
}

/** Shell shown immediately while useSearchParams resolves — screen opens without waiting. */
function HITLPageShell() {
  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col p-6">
      <div className="mb-6 shrink-0 space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
          Verification
        </h1>
        <p className="mt-1 text-sm text-[#64748b]">
          Review documents requiring human verification — compare submitted documents against official registry records
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
        <div className="lg:w-64 shrink-0 space-y-2 rounded-lg border border-border bg-muted/30 p-4">
          <p className="text-sm font-medium text-muted-foreground">Documents</p>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-muted" />
            ))}
          </div>
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 lg:flex-row">
          <div className="flex min-h-[400px] min-w-0 flex-1 flex-col rounded-lg border border-border bg-muted/30">
            <div className="flex flex-1 items-center justify-center p-8">
              <p className="text-sm text-muted-foreground">Select a document to view</p>
            </div>
          </div>
          <div className="flex min-h-[400px] min-w-0 flex-1 flex-col rounded-lg border border-border bg-muted/30">
            <div className="flex flex-1 items-center justify-center p-8">
              <p className="text-sm text-muted-foreground">Verification summary</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function VerificationDashboardPage() {
  return (
    <Suspense fallback={<HITLPageShell />}>
      <VerificationDashboardContent />
    </Suspense>
  );
}
