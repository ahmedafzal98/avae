"use client";

import { cn } from "@/lib/utils";

export interface DocumentViewerPaneProps {
  children?: React.ReactNode;
  /** When true, show PDF viewer; when false, show placeholder */
  hasDocument?: boolean;
  className?: string;
}

/**
 * Document viewer container. No redundant toolbar — the PDF viewer
 * has its own built-in toolbar with zoom, page nav. Use Ctrl+scroll to zoom.
 */
export function DocumentViewerPane({
  children,
  hasDocument = false,
  className,
}: DocumentViewerPaneProps) {
  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white",
        className
      )}
    >
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
        {hasDocument && children ? (
          <div className="flex h-full min-h-0 w-full flex-col">
            {children}
          </div>
        ) : (
          <div className="flex min-h-full flex-1 items-center justify-center">
            <div className="rounded-lg border border-slate-200 bg-white px-8 py-6 shadow-sm">
              <p className="text-sm font-medium text-slate-500">
                Select a document to view
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Ctrl+scroll to zoom • Use toolbar for navigation
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
