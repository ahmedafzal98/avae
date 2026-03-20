"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { highlightPlugin, Trigger } from "@react-pdf-viewer/highlight";
import type { HighlightArea, RenderHighlightsProps } from "@react-pdf-viewer/highlight";
import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";
import "@react-pdf-viewer/highlight/lib/styles/index.css";
import "./document-preview.css";

const PDF_WORKER_URL = `https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`;

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.15;
const DEFAULT_SCALE = 1.25;

export interface DocumentPreviewProps {
  /** PDF URL to display (e.g. from GET /documents/{id}/pdf) */
  fileUrl: string | null;
  /** Optional filename for empty state */
  filename?: string;
  /** Highlight area when user hovers/clicks a verification row (red=discrepancy, green=verified) */
  highlightArea?: HighlightArea | null;
  /** Highlight color: "red" for discrepancy, "green" for verified */
  highlightColor?: "red" | "green";
  className?: string;
}

/**
 * PDF viewer for Verification Dashboard.
 * - Mouse wheel + Ctrl/Cmd to zoom (no +/- buttons needed)
 * - Larger default viewport (125%)
 * - No sidebar — full width for document
 * - Modern, clean styling
 */
export function DocumentPreview({
  fileUrl,
  filename,
  highlightArea,
  highlightColor = "green",
  className = "",
}: DocumentPreviewProps) {
  const [scale, setScale] = useState(DEFAULT_SCALE);
  const containerRef = useRef<HTMLDivElement>(null);

  // Must be called at top level — defaultLayoutPlugin uses hooks internally.
  // Do NOT wrap in useMemo; that violates Rules of Hooks.
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: () => [],
  });

  const renderHighlights = useCallback(
    (props: RenderHighlightsProps) => {
      if (!highlightArea || highlightArea.pageIndex !== props.pageIndex) {
        return <></>;
      }
      const bgColor =
        highlightColor === "red" ? "rgba(220, 38, 38, 0.35)" : "rgba(5, 150, 105, 0.35)";
      return (
        <div
          style={{
            ...props.getCssProperties(highlightArea, props.rotation),
            background: bgColor,
            borderRadius: "2px",
          }}
        />
      );
    },
    [highlightArea, highlightColor]
  );

  const highlightPluginInstance = highlightPlugin({
    renderHighlights,
    trigger: Trigger.None,
  });

  useEffect(() => {
    if (highlightArea && highlightPluginInstance.jumpToHighlightArea) {
      highlightPluginInstance.jumpToHighlightArea(highlightArea);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only jump when highlightArea changes
  }, [highlightArea]);

  useEffect(() => {
    const el = containerRef.current;
    const zoomTo =
      defaultLayoutPluginInstance.toolbarPluginInstance?.zoomPluginInstance?.zoomTo;
    if (!el || !zoomTo) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        setScale((prev) => {
          const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
          const newScale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta));
          zoomTo(newScale);
          return newScale;
        });
      }
    };

    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      el.removeEventListener("wheel", handleWheel);
    };
  }, [defaultLayoutPluginInstance]);

  if (!fileUrl) {
    return (
      <div
        className={`flex flex-1 flex-col items-center justify-center p-8 text-muted-foreground ${className}`}
      >
        <p className="text-sm">Select a document to view</p>
        {filename && (
          <p className="mt-1 text-xs opacity-80">Document: {filename}</p>
        )}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex h-full w-full flex-col overflow-hidden ${className}`}
    >
      <Worker workerUrl={PDF_WORKER_URL}>
        <Viewer
          fileUrl={fileUrl}
          plugins={[defaultLayoutPluginInstance, highlightPluginInstance]}
          defaultScale={DEFAULT_SCALE}
          onZoom={(e) => setScale(e.scale)}
          renderLoader={(percentages) => (
            <div className="flex h-full items-center justify-center bg-slate-50">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-slate-600" />
                <span className="text-sm text-slate-500">
                  Loading… {percentages}%
                </span>
              </div>
            </div>
          )}
        />
      </Worker>
    </div>
  );
}
