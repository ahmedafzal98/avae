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
import { getOfficialRegistryName } from "@/lib/registry-labels";
import {
  hitlOverride,
  hitlManualCorrection,
  hitlRequestClientRemediation,
  getRemediationEmailDraft,
} from "@/lib/api";
import { Copy, Mail, Loader2, CheckCircle2, Pencil, Send, AlertCircle } from "lucide-react";
import { useOfficerLevel } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

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
        handleApiError(err);
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
        className="flex max-h-[90vh] flex-col overflow-hidden border-0 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.25)] sm:max-w-xl"
        showCloseButton={true}
      >
        <div className="relative flex min-h-0 flex-1 flex-col">
          {loading && (
            <div
              className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-white/90 backdrop-blur-sm"
              aria-live="polite"
              aria-label="Applying action"
            >
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-slate-100 p-3">
                  <Loader2 className="size-6 animate-spin text-slate-600" aria-hidden />
                </div>
                <p className="text-sm font-medium text-slate-700">Applying…</p>
              </div>
            </div>
          )}

        <DialogHeader className="shrink-0 space-y-3 border-b border-slate-100 pb-2">
          <div className="flex items-center gap-2">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <AlertCircle className="size-4" strokeWidth={2} />
            </span>
            <DialogTitle className="text-base font-semibold text-slate-800">
              {buildErrorTitle(selectedRow, discrepancyRows)}
            </DialogTitle>
          </div>
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
              {error}
            </div>
          )}
          <DialogDescription className="text-sm text-slate-600 leading-relaxed">
            {buildDiscrepancyDescription(selectedRow, discrepancyRows, getOfficialRegistryName(verification?.audit_target ?? ""))}
          </DialogDescription>
        </DialogHeader>

        {/* Action options — card-style selectable, scrollable */}
        <div className="min-h-0 flex-1 overflow-y-auto py-4">
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Choose resolution
          </p>

          {/* Confirm Correct Value */}
          <label
            className={cn(
              "flex cursor-pointer gap-4 rounded-xl border-2 p-4 transition-all",
              action === "override"
                ? "border-emerald-500 bg-emerald-50/50 shadow-sm"
                : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
            )}
          >
            <input
              type="radio"
              name="hitl-action"
              checked={action === "override"}
              onChange={() => setAction("override")}
              className="sr-only"
            />
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
              <CheckCircle2 className="size-5" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-slate-800">Confirm Correct Value</span>
              <p className="mt-0.5 text-sm text-slate-500">
                Document value is correct. You take responsibility.
              </p>
            </div>
          </label>
          {action === "override" && (
            <div className="ml-14 space-y-2 rounded-lg bg-white p-4 ring-1 ring-slate-200">
              <label htmlFor="hitl-justification" className="text-sm font-medium text-slate-700">
                Justification <span className="text-rose-500">*</span>
              </label>
              <textarea
                id="hitl-justification"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Explain the basis for this decision (required for audit)"
                maxLength={500}
                rows={3}
                className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
              <p className="text-xs text-slate-400">{justification.length}/500</p>
            </div>
          )}

          {/* Enter Correct Value */}
          <label
            className={cn(
              "flex cursor-pointer gap-4 rounded-xl border-2 p-4 transition-all",
              action === "manual"
                ? "border-emerald-500 bg-emerald-50/50 shadow-sm"
                : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
            )}
          >
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
              className="sr-only"
            />
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <Pencil className="size-5" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-slate-800">Enter Correct Value</span>
              <p className="mt-0.5 text-sm text-slate-500">
                Update the value; we will re-check against the official record.
              </p>
            </div>
          </label>
          {action === "manual" && rowsToCorrect.length > 0 && (
            <div className="ml-14 space-y-3 rounded-lg bg-white p-4 ring-1 ring-slate-200">
              {rowsToCorrect.map((r) => (
                <div key={r.field} className="space-y-1.5">
                  <label htmlFor={`hitl-correction-${r.field}`} className="text-sm font-medium text-slate-700">
                    {formatFieldName(r.field)}
                  </label>
                  <input
                    id={`hitl-correction-${r.field}`}
                    type="text"
                    value={corrections[r.field] ?? ""}
                    onChange={(e) =>
                      setCorrections((prev) => ({ ...prev, [r.field]: e.target.value }))
                    }
                    placeholder={`Official record: ${formatValue(r.api_value)}`}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Request Client Remediation */}
          <label
            className={cn(
              "flex cursor-pointer gap-4 rounded-xl border-2 p-4 transition-all",
              action === "remediation"
                ? "border-emerald-500 bg-emerald-50/50 shadow-sm"
                : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
            )}
          >
            <input
              type="radio"
              name="hitl-action"
              checked={action === "remediation"}
              onChange={() => {
                setAction("remediation");
                setEmailDraft(null);
              }}
              className="sr-only"
            />
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <Send className="size-5" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-slate-800">Request Client Remediation</span>
              <p className="mt-0.5 text-sm text-slate-500">
                Ask the client to upload a corrected document.
              </p>
            </div>
          </label>
          {action === "remediation" && (
            <div className="ml-14 space-y-3 rounded-lg bg-white p-4 ring-1 ring-slate-200">
              <div className="space-y-1.5">
                <label htmlFor="hitl-remediation-message" className="text-sm font-medium text-slate-700">
                  Message to client (optional)
                </label>
                <textarea
                  id="hitl-remediation-message"
                  value={remediationMessage}
                  onChange={(e) => setRemediationMessage(e.target.value)}
                  placeholder="Add instructions or context…"
                  rows={2}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateEmailDraft}
                disabled={emailDraftLoading}
                className="gap-2 border-slate-200 font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900"
              >
                {emailDraftLoading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Mail className="size-4" />
                )}
                Generate Email Draft
              </Button>
              {emailDraft && (
                <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/30 p-4">
                  <div>
                    <span className="text-xs font-medium text-slate-500">Subject</span>
                    <p className="mt-0.5 text-sm font-medium text-slate-800">{emailDraft.subject}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500">Body</span>
                    <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-3 text-xs text-slate-600 ring-1 ring-slate-200" role="region" aria-label="Email body">
                      {emailDraft.body}
                    </pre>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyToClipboard}
                    className="gap-2 text-slate-600 hover:bg-slate-100 hover:text-slate-800"
                  >
                    <Copy className="size-4" />
                    {copySuccess ? "Copied!" : "Copy to clipboard"}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
        </div>

        <DialogFooter className="-mx-4 -mb-4 shrink-0 flex-col-reverse gap-3 rounded-b-xl border-t border-slate-100 bg-slate-50/50 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs font-medium text-slate-400">
            Authorized as {officerLevel}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={loading}
              className="border-slate-200 font-medium text-slate-600 hover:bg-white hover:text-slate-800"
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={
                (!canConfirmOverride && !canConfirmManual && !canConfirmRemediation) || loading
              }
              className="font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
            >
              {loading
                ? "Applying…"
                : action === "manual"
                  ? "Approve & Continue"
                  : action === "remediation"
                    ? "Send remediation request"
                    : action === "override"
                      ? "Approve & Continue"
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

/** Task 6.2: Error title — Action Required (authority-based, not technical) */
function buildErrorTitle(
  selectedRow: VerificationFieldRow | null | undefined,
  discrepancyRows: VerificationFieldRow[]
): string {
  const base = "Action Required";
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

/** Business-friendly discrepancy description (plain English, no API jargon) */
function buildDiscrepancyDescription(
  selectedRow: VerificationFieldRow | null | undefined,
  discrepancyRows: VerificationFieldRow[],
  registryName: string
): React.ReactNode {
  const genericReason = `The value on the submitted document does not match the active registration at ${registryName}.`;
  if (selectedRow) {
    return (
      <div className="space-y-3">
        <p className="text-slate-600">{genericReason}</p>
        <div className="grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3 ring-1 ring-slate-200">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">From Your Document</p>
            <p className="mt-1 font-mono text-sm font-medium text-slate-800">{formatValue(selectedRow.document_value)}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Official Record</p>
            <p className="mt-1 font-mono text-sm font-medium text-slate-800">{formatValue(selectedRow.api_value)}</p>
          </div>
        </div>
      </div>
    );
  }
  if (discrepancyRows.length > 0) {
    return (
      <div className="space-y-3">
        <p className="text-slate-600">
          {discrepancyRows.length} field{discrepancyRows.length !== 1 ? "s" : ""} require resolution:
        </p>
        <div className="space-y-2">
          {discrepancyRows.map((r) => (
            <div
              key={r.field}
              className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 ring-1 ring-slate-200"
            >
              <span className="text-sm font-medium text-slate-700">{formatFieldName(r.field)}</span>
              <span className="font-mono text-xs text-slate-500">
                {formatValue(r.document_value)} → {formatValue(r.api_value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return <p className="text-slate-600">No discrepancies to resolve.</p>;
}
