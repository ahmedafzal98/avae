"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Info, Sparkles, Loader2, FileStack } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { VerificationFieldRow, SimilarOverrideSuggestion } from "@/lib/api";
import { getSimilarOverrides } from "@/lib/api";

export interface SimilarOverridesPanelProps {
  className?: string;
  checkpointId?: string;
  selectedRow?: VerificationFieldRow | null;
  /**
   * Phase 8.3: When officer clicks "Apply same", we pre-fill HITL modal
   * (officer still confirms via the modal's confirm button).
   */
  onApplySame?: (suggestion: SimilarOverrideSuggestion) => void;
}

/**
 * Phase 8.2/8.3: Similar past overrides panel.
 *
 * Fetches suggestions from Semantic Memory (when backend is available).
 * If the endpoint is missing, the UI falls back to sample suggestions so
 * the interaction flow can still be tested.
 */
export function SimilarOverridesPanel({
  className,
  checkpointId,
  selectedRow = null,
  onApplySame,
}: SimilarOverridesPanelProps) {
  const field = selectedRow?.field ?? null;

  const { data, isLoading, error } = useQuery({
    queryKey: ["similar-overrides", checkpointId, field],
    enabled: Boolean(checkpointId),
    queryFn: () => getSimilarOverrides(checkpointId!, { field }),
  });

  const suggestionsFromBackend = data?.suggestions ?? [];

  // Only show sample suggestions when the backend call itself fails.
  const showSamples = !isLoading && Boolean(error) && Boolean(selectedRow);

  const sampleSuggestions: SimilarOverrideSuggestion[] = showSamples
    ? [
        {
          id: "sample-1",
          field: field ?? undefined,
          confidence: 0.42,
          justification: `Based on prior officer override reasoning for ${field ?? "this field"}, the API value should be treated as authoritative when the document extraction conflicts.`,
          source_override_memory_ids: ["om-001", "om-003"],
        },
        {
          id: "sample-2",
          field: field ?? undefined,
          confidence: 0.31,
          justification: `Previous similar cases show consistent external evidence even when document parsing produces a mismatching value. Using the API record reduces downstream reconciliation errors.`,
          source_override_memory_ids: ["om-002"],
        },
      ]
    : [];

  const suggestions = showSamples ? sampleSuggestions : suggestionsFromBackend;

  return (
    <section
      className={cn(
        "flex-none rounded-lg border border-border bg-muted/30 p-4 flex flex-col gap-3",
        className
      )}
      aria-label="Similar past overrides"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Sparkles className="size-4" aria-hidden />
            Similar past overrides
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Suggestions based on your past HITL override/manual decisions.
          </p>
        </div>

        <div className="rounded-md border border-border bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground whitespace-nowrap">
          {selectedRow?.field ? `Context: ${selectedRow.field}` : "Select a discrepancy field"}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-background/30 p-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Info className="size-4" aria-hidden />
          <span>Click a suggestion to pre-fill the justification ledger.</span>
        </div>

        <div className="mt-3 flex items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground">
            {checkpointId ? `Checkpoint: ${checkpointId}` : "Checkpoint: —"}
          </div>

          {isLoading ? (
            <span className="inline-flex items-center gap-2 text-xs text-muted-foreground" aria-live="polite">
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
              Loading suggestions…
            </span>
          ) : showSamples ? (
            <span className="inline-flex items-center gap-2 text-xs text-muted-foreground" aria-live="polite">
              <Info className="size-3.5" aria-hidden />
              Backend not available; showing sample suggestions
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {suggestions.length > 0 ? `${suggestions.length} suggestion(s)` : "No suggestions"}
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-col gap-2">
          {(!selectedRow && !isLoading) ? (
            <p className="text-xs text-muted-foreground">
              Select a discrepancy row first to scope similar past overrides.
            </p>
          ) : null}

          {suggestions.map((s) => (
            <div
              key={s.id}
              className="rounded-md border border-border bg-background/50 p-3"
              aria-label={`Similar override suggestion ${s.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground">
                      Suggestion
                    </span>
                    {typeof s.confidence === "number" && (
                      <span className="text-[11px] text-muted-foreground">
                        Reliability {Math.round(s.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-xs text-foreground">
                    {s.justification}
                  </p>
                </div>

                <div className="shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => onApplySame?.(s)}
                    disabled={!selectedRow || isLoading}
                    aria-label={`Apply same justification (${s.id})`}
                  >
                    Apply same
                  </Button>
                </div>
              </div>

              {/* Task 8.4: Provenance — which override_memories IDs informed this suggestion */}
              <div className="mt-2 flex items-start gap-2 rounded border border-border/60 bg-muted/20 px-2 py-1.5" role="group" aria-label="Provenance">
                <FileStack className="size-3.5 shrink-0 mt-0.5 text-muted-foreground" aria-hidden />
                <div className="min-w-0">
                  <span className="text-[11px] font-medium text-muted-foreground">Provenance</span>
                  {s.source_override_memory_ids && s.source_override_memory_ids.length > 0 ? (
                    <p className="mt-0.5 text-[11px] text-foreground font-mono" title="Override memory IDs that informed this suggestion">
                      {s.source_override_memory_ids.join(", ")}
                    </p>
                  ) : (
                    <p className="mt-0.5 text-[11px] text-muted-foreground italic">
                      No override_memories IDs linked
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}

          {!isLoading && selectedRow && suggestions.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No similar past overrides found for this discrepancy field yet.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

