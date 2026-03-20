"use client";

import { useState, useEffect, useRef } from "react";
import type React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { DocumentVerificationResponse, VerificationFieldRow } from "@/lib/api";
import {
  hitlOverride,
  hitlManualCorrection,
  hitlRequestClientRemediation,
  getRemediationEmailDraft,
} from "@/lib/api";
import { Copy, Mail, Loader2 } from "lucide-react";
import { useOfficerLevel } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

export interface HITLModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  checkpointId: string;
  verification: DocumentVerificationResponse | null | undefined;
  /** When set, modal was opened by clicking this discrepancy row */
  selectedRow?: VerificationFieldRow | null;
  /**
   * Phase 8.3: pre-fill override justification (used by SimilarOverridesPanel "Apply same").
   * Officer still confirms in this modal.
   */
  initialOverrideJustification?: string | null;
  onSuccess?: () => void;
  /** Task 6.6: Called when an API call fails */
  onError?: (message: string) => void;
}

/**
 * HITL Modal (Task 6.1) — triggered by discrepancy row click or Resolve button.
 * Tasks 6.2–6.8 will add content: error title, Override, Manual Correction, Request Client Remediation.
 */
export function HITLModal({
  open,
  onOpenChange,
  checkpointId,
  verification,
  selectedRow = null,
  initialOverrideJustification = null,
  onSuccess,
  onError,
}: HITLModalProps) {
  const discrepancyRows = verification?.rows?.filter((r) => r.status === "DISCREPANCY") ?? [];
  const officerLevel = useOfficerLevel();

  const [action, setAction] = useState<"override" | "manual" | "remediation" | null>(null);
  const [justification, setJustification] = useState("");
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [remediationMessage, setRemediationMessage] = useState("");
  const [emailDraft, setEmailDraft] = useState<{ subject: string; body: string } | null>(null);
  const [emailDraftLoading, setEmailDraftLoading] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasAppliedInitialJustificationRef = useRef(false);

  const handleClose = () => {
    onOpenChange(false);
    setAction(null);
    setJustification("");
    setCorrections({});
    setRemediationMessage("");
    setEmailDraft(null);
    setError(null);
  };

  const handleApiError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : String(err);
    setError(msg);
    onError?.(msg);
  };

  const canConfirmOverride = action === "override" && justification.trim().length >= 1 && justification.length <= 500;

  const rowsToCorrect = selectedRow ? [selectedRow] : discrepancyRows;
  const canConfirmManual =
    action === "manual" &&
    rowsToCorrect.length > 0 &&
    rowsToCorrect.every((r) => (corrections[r.field] ?? "").trim().length > 0);

  const canConfirmRemediation = action === "remediation";

  /** Task 6.7: Auto-fetch email draft for preview when remediation is selected */
  useEffect(() => {
    if (action !== "remediation" || emailDraft || emailDraftLoading) return;
    let cancelled = false;
    setEmailDraftLoading(true);
    getRemediationEmailDraft(checkpointId)
      .then((draft) => {
        if (!cancelled) {
          setEmailDraft(draft);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err);
          setError(msg);
          onError?.(msg);
        }
      })
      .finally(() => {
        if (!cancelled) setEmailDraftLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- emailDraft/emailDraftLoading excluded to avoid refetch loops
  }, [action, checkpointId]);

  // Phase 8.3: when "Apply same" is clicked, pre-fill the override justification
  // so the officer can review and confirm.
  useEffect(() => {
    if (!open) return;
    if (!initialOverrideJustification) return;
    if (hasAppliedInitialJustificationRef.current) return;

    setAction("override");
    setJustification(initialOverrideJustification);
    setError(null);
    hasAppliedInitialJustificationRef.current = true;
    // Intentionally not touching corrections/remediationMessage here:
    // switching actions is enough; officer still confirms.
  }, [open, initialOverrideJustification]);

  useEffect(() => {
    if (!open) hasAppliedInitialJustificationRef.current = false;
  }, [open]);

  const handleGenerateEmailDraft = async () => {
    setEmailDraftLoading(true);
    setEmailDraft(null);
    try {
      const draft = await getRemediationEmailDraft(
        checkpointId,
        remediationMessage.trim() || undefined
      );
      setEmailDraft(draft);
      setError(null);
    } catch (err) {
      handleApiError(err);
    } finally {
      setEmailDraftLoading(false);
    }
  };

  const handleCopyToClipboard = async () => {
    if (!emailDraft) return;
    const text = `Subject: ${emailDraft.subject}\n\n${emailDraft.body}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  const handleConfirm = async () => {
    if (action === "override" && canConfirmOverride) {
      setLoading(true);
      setError(null);
      try {
        await hitlOverride(checkpointId, {
          field: selectedRow?.field ?? undefined,
          justification: justification.trim(),
        });
        onSuccess?.();
        handleClose();
      } catch (err) {
        handleApiError(err);
      } finally {
        setLoading(false);
      }
    } else if (action === "manual" && canConfirmManual) {
      setLoading(true);
      setError(null);
      try {
        const correctionsPayload: Record<string, unknown> = {};
        for (const r of rowsToCorrect) {
          const val = corrections[r.field]?.trim();
          if (val != null) correctionsPayload[r.field] = val;
        }
        await hitlManualCorrection(checkpointId, correctionsPayload);
        onSuccess?.();
        handleClose();
      } catch (err) {
        handleApiError(err, "Manual correction");
      } finally {
        setLoading(false);
      }
    } else if (action === "remediation" && canConfirmRemediation) {
      setLoading(true);
      setError(null);
      try {
        await hitlRequestClientRemediation(
          checkpointId,
          remediationMessage.trim() || undefined
        );
        onSuccess?.();
        handleClose();
      } catch (err) {
        handleApiError(err);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-xl"
        showCloseButton={true}
      >
        <div className="relative grid gap-4">
          {loading && (
            <div
              className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-background/80"
              aria-live="polite"
              aria-label="Applying action"
            >
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="size-8 animate-spin text-muted-foreground" aria-hidden />
                <div className="flex gap-2">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </div>
            </div>
          )}
        <DialogHeader>
          <DialogTitle className="text-destructive">
            {buildErrorTitle(selectedRow, discrepancyRows)}
          </DialogTitle>
          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <DialogDescription className="mt-1 space-y-2">
            {buildDiscrepancyDescription(selectedRow, discrepancyRows)}
          </DialogDescription>
        </DialogHeader>

        {/* Task 6.3: Override | 6.4: Manual Correction | 6.5: Request Client Remediation */}
        <div className="space-y-4 py-2">
          {/* Override (Task 6.3) */}
          <div className="space-y-2">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="radio"
                name="hitl-action"
                checked={action === "override"}
                onChange={() => setAction("override")}
                className="mt-1"
              />
              <div>
                <span className="font-medium">Override</span>
                <p className="text-sm text-muted-foreground">
                  Force verification based on internal evidence. Officer takes responsibility.
                </p>
              </div>
            </label>
            {action === "override" && (
              <div className="ml-6 space-y-1">
                <label htmlFor="hitl-justification" className="text-sm font-medium">
                  Justification Ledger <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="hitl-justification"
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Explain the basis for this override (required, max 500 characters)"
                  maxLength={500}
                  rows={3}
                  className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
                <p className="text-xs text-muted-foreground">
                  {justification.length}/500 characters
                </p>
              </div>
            )}
          </div>

          {/* Manual Correction (Task 6.4) */}
          <div className="space-y-2">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="radio"
                name="hitl-action"
                checked={action === "manual"}
                onChange={() => {
                  setAction("manual");
                  const initial: Record<string, string> = {};
                  for (const r of rowsToCorrect) {
                    const val = r.document_value;
                    initial[r.field] =
                      val != null && val !== "" ? String(val) : "";
                  }
                  setCorrections(initial);
                }}
                className="mt-1"
              />
              <div>
                <span className="font-medium">Manual Correction</span>
                <p className="text-sm text-muted-foreground">
                  Enter the corrected value; submit re-runs verification.
                </p>
              </div>
            </label>
            {action === "manual" && rowsToCorrect.length > 0 && (
              <div className="ml-6 space-y-3">
                {rowsToCorrect.map((r) => (
                  <div key={r.field} className="space-y-1">
                    <label htmlFor={`hitl-correction-${r.field}`} className="text-sm font-medium">
                      {formatFieldName(r.field)}
                    </label>
                    <input
                      id={`hitl-correction-${r.field}`}
                      type="text"
                      value={corrections[r.field] ?? ""}
                      onChange={(e) =>
                        setCorrections((prev) => ({ ...prev, [r.field]: e.target.value }))
                      }
                      placeholder={`Corrected value (API: ${formatValue(r.api_value)})`}
                      className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Request Client Remediation (Task 6.5) */}
          <div className="space-y-2">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="radio"
                name="hitl-action"
                checked={action === "remediation"}
                onChange={() => {
                  setAction("remediation");
                  setEmailDraft(null);
                }}
                className="mt-1"
              />
              <div>
                <span className="font-medium">Request Client Remediation</span>
                <p className="text-sm text-muted-foreground">
                  Mark document for client fix. Generate templated email to notify the client.
                </p>
              </div>
            </label>
            {action === "remediation" && (
              <div className="ml-6 space-y-3">
                <div className="space-y-1">
                  <label htmlFor="hitl-remediation-message" className="text-sm font-medium">
                    Message to client (optional)
                  </label>
                  <textarea
                    id="hitl-remediation-message"
                    value={remediationMessage}
                    onChange={(e) => setRemediationMessage(e.target.value)}
                    placeholder="Add instructions or context for the client…"
                    rows={2}
                    className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateEmailDraft}
                  disabled={emailDraftLoading}
                  className="gap-1.5"
                >
                  {emailDraftLoading ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Mail className="size-3.5" />
                  )}
                  Generate Email Draft
                </Button>
                {emailDraft && (
                  <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Subject:</span>
                      <p className="text-sm">{emailDraft.subject}</p>
                    </div>
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Body:</span>
                      <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-xs" role="region" aria-label="Email body">
                        {emailDraft.body}
                      </pre>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyToClipboard}
                      className="gap-1.5"
                    >
                      <Copy className="size-3.5" />
                      {copySuccess ? "Copied!" : "Copy to clipboard"}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="order-last text-xs text-muted-foreground sm:order-first">
            AUTHORIZED AS {officerLevel}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={
                (!canConfirmOverride && !canConfirmManual && !canConfirmRemediation) || loading
              }
            >
              {loading
                ? "Applying…"
                : action === "manual"
                  ? "Submit correction"
                  : action === "remediation"
                    ? "Send remediation request"
                    : action === "override"
                      ? "Confirm override"
                      : "Choose an action"}
            </Button>
          </div>
        </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}

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

/** Task 6.2: Error title e.g. "VALIDATION ERROR - CRN 0842" */
function buildErrorTitle(
  selectedRow: VerificationFieldRow | null | undefined,
  discrepancyRows: VerificationFieldRow[]
): string {
  const base = "VALIDATION ERROR";
  if (selectedRow) {
    const identifier = getFieldIdentifier(selectedRow.field, selectedRow.document_value);
    return identifier ? `${base} - ${identifier}` : `${base} - ${formatFieldName(selectedRow.field)}`;
  }
  if (discrepancyRows.length > 0) {
    const first = discrepancyRows[0];
    const identifier = getFieldIdentifier(first.field, first.document_value);
    return identifier ? `${base} - ${identifier}` : `${base} - ${discrepancyRows.length} field(s)`;
  }
  return base;
}

function getFieldIdentifier(field: string, value: unknown): string | null {
  const str = formatValue(value);
  if (!str || str === "—") return null;
  if (field === "company_number") return `CRN ${str}`;
  if (field === "reference_number") return `RRN ${str}`;
  if (field === "title_number") return `Title ${str}`;
  if (field === "property_address" && str.length > 40) return `${str.slice(0, 40)}…`;
  if (field === "property_address") return str;
  return str;
}

/** Task 6.2: Discrepancy description */
function buildDiscrepancyDescription(
  selectedRow: VerificationFieldRow | null | undefined,
  discrepancyRows: VerificationFieldRow[]
): React.ReactNode {
  if (selectedRow) {
    return (
      <>
        <p>
          <strong>{formatFieldName(selectedRow.field)}</strong> does not match the external API record.
        </p>
        <div className="rounded-md border border-border bg-muted/30 p-3 font-mono text-xs">
          <div>
            <span className="text-muted-foreground">Document: </span>
            {formatValue(selectedRow.document_value)}
          </div>
          <div className="mt-1">
            <span className="text-muted-foreground">API: </span>
            {formatValue(selectedRow.api_value)}
          </div>
        </div>
      </>
    );
  }
  if (discrepancyRows.length > 0) {
    return (
      <>
        <p>{discrepancyRows.length} field(s) require resolution:</p>
        <ul className="list-inside list-disc space-y-1">
          {discrepancyRows.map((r) => (
            <li key={r.field}>
              <strong>{formatFieldName(r.field)}</strong>: {formatValue(r.document_value)} vs {formatValue(r.api_value)}
            </li>
          ))}
        </ul>
      </>
    );
  }
  return <p>No discrepancies to resolve.</p>;
}
